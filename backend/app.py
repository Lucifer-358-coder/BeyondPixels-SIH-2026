"""BeyondPixels local-demo screening API. NOT production-ready or border-deployable."""
from __future__ import annotations

import os
import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS
from media import InvalidMedia, MAX_BYTES, open_document_image
from mrz import inspect_passport_mrz
from mrz_ocr import extract_td3_mrz
from extra_mrz import inspect_extra_from_image
from c2pa_check import verify_content_credentials
from services import extract_text
from ocr_fields import extract_labelled_fields, extract_mrz_display_fields
from expiry_ocr_bridge import integrate_expiry_ocr
from image_detector import detect_image
from deepfake_service import analyze_deepfake
from document_consistency import assess_document_consistency
from tampering_localization import localize_document_pixel_differences
from single_image_review import localize_disputed_printed_fields
from visual_artifact_review import review_jpeg_residuals
from copy_move_review import review_copy_move
from document_portrait_review import review_document_portrait
from portrait_face_comparison import compare_document_face
from metadata_provenance import inspect_file_metadata
from standalone_tampering_review import assess_standalone_tampering_review
from portrait_replacement_review import review_portrait_replacement
from authorized_similarity import review_authorized_references, MAX_REFERENCES
from review_report import build_review_report
from pan_document_review import inspect_pan_document  # BP_PAN_DOCUMENT_EVIDENCE_V1
from review_audit import create_review_ref, valid_review_ref, record_action, fetch_events, VALID_ACTIONS

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = (3 + MAX_REFERENCES) * MAX_BYTES + 524288
# Only local web-dev origins. Never configure permissive wildcard CORS for deployment.
CORS(app, origins=r"^http://(localhost|127\.0\.0\.1)(:[0-9]+)?$")


from ui_capabilities import ui_capabilities


@app.get("/v1/capabilities")
def capabilities():
    return jsonify(ui_capabilities())


@app.get("/health")
def health():
    return jsonify({"status": "ok", "app": "BeyondPixels", "version": "0.1-demo"})


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "File exceeds the 8 MB image limit"}), 413


@app.post("/v1/screen")
def screen():
    # Local-demo token: the frontend asks the operator to enter it at runtime.
    # Replace with proper authentication and role-based access before real data.
    expected = os.environ.get("BEYONDPIXELS_DEMO_TOKEN", "")
    if not expected:
        return jsonify({"error": "Server demo token is not configured"}), 503
    import hmac
    supplied = request.headers.get("Authorization", "")
    if not hmac.compare_digest(supplied, f"Bearer {expected}"):
        return jsonify({"error": "Unauthorized"}), 401
    uploaded = request.files.get("image")
    if uploaded is None:
        return jsonify({"error": "Send a multipart field named image"}), 400
    data = uploaded.stream.read(MAX_BYTES + 1)
    try:
        image = open_document_image(data)
    except InvalidMedia as exc:
        return jsonify({"error": str(exc)}), 400
    # Optional trusted reference is used ONLY for lossless, aligned pixel
    # comparison in Document Verification. Do not upload it to media models.
    reference_file = request.files.get("reference_image")
    reference = None
    reference_bytes = None
    if reference_file is not None:
        reference_bytes = reference_file.stream.read(MAX_BYTES + 1)
        try:
            reference = open_document_image(reference_bytes)
        except InvalidMedia as exc:
            return jsonify({"error": "Invalid reference image: " + str(exc)}), 400
    tampering = localize_document_pixel_differences(image, data, reference, reference_bytes)
    ocr = extract_text(image)
    # General OCR supplies labelled fields; dedicated MRZ OCR reads the two
    # machine-readable lines. Preserve the v2 MRZ extraction path when adding UI fields.
    # Do not alter an extracted MRZ or its check digits to make validation pass.
    mrz_extraction = {"status": "not_checked", "text": ""}
    if ocr["status"] == "completed":
        # TD1 ID cards and TD2 travel documents: conservative literal OCR,
        # no checksum-based character repair or country-specific claims.
        additional = inspect_extra_from_image(image, ocr.get("text", ""))
        if additional["status"] != "not_detected":
            mrz = additional
            mrz_extraction = {"status": "detected", "text": ""}
        else:
            # Preserve the existing photographed TD3 passport path unchanged.
            mrz_extraction = extract_td3_mrz(image)
            if mrz_extraction["status"] == "detected":
                mrz = inspect_passport_mrz(mrz_extraction["text"])
            else:
                mrz = inspect_passport_mrz(ocr.get("text", ""))
    else:
        mrz = {"status": "not_checked", "document_type": "unknown", "checks": {}}
    # Document screening is a separate workflow. A CIFAKE whole-image score
    # cannot establish forgery and must not be computed for a document upload.
    # Keep legacy response keys as explicit non-applicable values for old clients.
    generation = {"status": "not_applicable", "decision": None, "ai_generated": None,
                  "message": "AI-image generation analysis is not run for document screening."}
    authenticity = generation  # legacy key retained; explicitly NOT an authenticity assessment
    fields = extract_labelled_fields(ocr.get("text", "")) if ocr["status"] == "completed" else {}
    if ocr["status"] == "completed":
        pan_review, fields = inspect_pan_document(image, ocr.get("text", ""), fields)
        if pan_review["document_type"] == "pan_card":
            # PAN cards have no expiry field; a spatial passport-expiry crop is inapplicable.
            expiry_extraction = {"status": "not_applicable", "method": None}
        else:
            fields, expiry_extraction = integrate_expiry_ocr(image, fields)
    else:
        pan_review = {"status": "not_assessed", "document_type": "unknown",
                      "finding": "ocr_unavailable", "checks": {}}
        expiry_extraction = {"status": "not_checked", "method": None}
    mrz_fields = extract_mrz_display_fields(
        mrz_extraction["text"] if mrz_extraction["status"] == "detected"
        else ocr.get("text", ""), mrz,
    ) if ocr["status"] == "completed" else {}
    consistency = assess_document_consistency(fields, mrz_fields, mrz, expiry_extraction)
    if pan_review["document_type"] == "pan_card":
        # Printed-vs-MRZ comparison is not applicable to a PAN card.
        consistency = dict(consistency, status="not_applicable", finding="pan_has_no_mrz",
                           message="PAN cards have no MRZ. See the separate PAN OCR-format observations; no field-to-issuer check was performed.")
    single_image = localize_disputed_printed_fields(image, consistency, fields)
    visual_artifacts = review_jpeg_residuals(image, data)
    copy_move = review_copy_move(image)
    portrait_review = review_document_portrait(image)
    provenance = inspect_file_metadata(data)
    # open_document_image converts to RGB, so its Pillow format is lost.
    # Determine the original encoded format from already-validated bytes.
    original_format = ('JPEG' if data.startswith(b'\xff\xd8\xff') else
                       'PNG' if data.startswith(b'\x89PNG\r\n\x1a\n') else '')
    content_credentials = verify_content_credentials(data, original_format)
    # Opt-in, user-supplied consented face PHOTO; no photo means no biometrics run.
    photo_file = request.files.get("comparison_photo")
    comparison_photo = None
    if photo_file is not None:
        photo_bytes = photo_file.stream.read(MAX_BYTES + 1)
        try:
            comparison_photo = open_document_image(photo_bytes)
        except InvalidMedia as exc:
            return jsonify({"error": "Invalid optional comparison photo: " + str(exc)}), 400
    # Each authorized reference is explicitly supplied for this request only.
    # Do not use face biometrics, remote search, or a persistent reference gallery.
    references = request.files.getlist("authorized_reference_images")
    if len(references) > MAX_REFERENCES:
        return jsonify({"error": "At most four authorized reference images are supported"}), 400
    reference_pairs = []
    for file in references:
        raw = file.stream.read(MAX_BYTES + 1)
        try:
            reference_pairs.append((open_document_image(raw), raw))
        except InvalidMedia as exc:
            return jsonify({"error": "Invalid authorized reference image: " + str(exc)}), 400
    image_similarity = review_authorized_references(image, data, reference_pairs)
    face_comparison = compare_document_face(image, comparison_photo)
    portrait_replacement = review_portrait_replacement(face_comparison)
    standalone_tampering = assess_standalone_tampering_review(
        consistency, mrz, single_image, visual_artifacts, copy_move, provenance
    )
    ocr_for_report = dict(ocr, finding=("structured_fields_observed" if fields else "no_structured_fields_observed"))
    report = build_review_report(
        ocr=ocr_for_report, mrz=mrz, consistency=consistency, localization=single_image,
        tampering=standalone_tampering, portrait=portrait_review,
        face=face_comparison, duplicates=image_similarity, c2pa=content_credentials,
    )
    if pan_review["document_type"] == "pan_card":
        report["observations"].insert(1, {
            "check": "PAN printed-field format", "status": pan_review["status"],
            "finding": pan_review["finding"]})
        report["observations"] = [
            dict(item, finding=("pan_has_no_mrz" if item["check"] == "MRZ consistency"
                                else "not_applicable_no_mrz" if item["check"] == "Printed-field consistency"
                                else item["finding"]),
                 status=("not_applicable" if item["check"] == "MRZ consistency" else item["status"]))
            for item in report["observations"]]
        if pan_review["status"] == "review_required":
            report["manual_review_items"].append("PAN printed-field format")
    review_ref = create_review_ref(expected)  # HMAC-bound, not stored until operator acts.
    attention = []
    if consistency["status"] == "review_required":
        attention.append("Document field consistency requires manual review; OCR or MRZ may be incorrect")
    if mrz["status"] in ("checksum_mismatch", "expired", "invalid_format"):
        attention.append("MRZ consistency or date check requires officer review")
    if expiry_extraction["status"] in ("ambiguous", "conflict"):
        attention.append("Expiry date OCR needs manual review; compare with the original document")
    if pan_review["status"] == "review_required":
        attention.append("PAN OCR-format observations need manual review; compare with the original")
    if not attention:
        attention.append("No supported automatic fraud conclusion; review original document and other evidence")
    return jsonify({
        "schema_version": "1.0", "app": "BeyondPixels",
        "screening_status": "manual_review" if (consistency["status"] == "review_required" or pan_review["status"] == "review_required" or mrz["status"] in ("checksum_mismatch", "expired", "invalid_format")) else "inconclusive",
        "ocr": {
            "status": ocr["status"],
            "raw_text_returned": False,
            "mrz_extraction_status": mrz_extraction["status"],
            "fields": fields,
            "expiry_extraction": expiry_extraction,
            "mrz_fields": mrz_fields,
            "mrz_fields_verified": False,
            "fields_verified": False,
            "message": "Extracted text may contain OCR errors; compare against the original image.",
        },
        "document_validation": mrz,
        "document_consistency": consistency,
        "document_format_review": pan_review,
        "image_generation": generation,
        "image_authenticity": authenticity,  # deprecated alias: does NOT assess authenticity
        "deepfake": {"status": "not_implemented"},
        "tampering_localization": tampering,  # legacy reference-only API
        "single_image_review": single_image,
        "visual_artifact_review": visual_artifacts,
        "copy_move_review": copy_move,
        "document_portrait_review": portrait_review,
        "provenance": provenance,
        "content_credentials": content_credentials,
        "face_verification": face_comparison,
        "portrait_replacement_review": portrait_replacement,
        "standalone_tampering_review": standalone_tampering,
        "image_similarity": image_similarity,
        "evidence_report": report,
        "review_ref": review_ref,
        "review_notes": attention,
        "disclaimer": "Screening aid only. Does not establish identity or fraud or authorize/reject travel.",
    })



def _authorized_demo_token():
    import hmac
    token = os.environ.get('BEYONDPIXELS_DEMO_TOKEN', '')
    supplied = request.headers.get('Authorization', '')
    return token if token and hmac.compare_digest(supplied, f'Bearer {token}') else None


@app.post('/v1/review')
def save_review():
    token = _authorized_demo_token()
    if not token:
        return jsonify({'error': 'Unauthorized'}), 401
    if not request.is_json or request.content_length is None or request.content_length > 1024:
        return jsonify({'error': 'Expected a small JSON review action'}), 400
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {'review_ref', 'action'}:
        return jsonify({'error': 'Expected review_ref and action only'}), 400
    if not valid_review_ref(token, data['review_ref']) or not isinstance(data['action'], str) or data['action'] not in VALID_ACTIONS:
        return jsonify({'error': 'Invalid review reference or action'}), 400
    try:
        event = record_action(data['review_ref'], data['action'])
    except (OSError, sqlite3.Error):
        return jsonify({'error': 'Local review log is unavailable'}), 503
    return jsonify(event), 201


@app.get('/v1/review/<review_ref>')
def read_review(review_ref):
    token = _authorized_demo_token()
    if not token:
        return jsonify({'error': 'Unauthorized'}), 401
    if not valid_review_ref(token, review_ref):
        return jsonify({'error': 'Invalid review reference'}), 400
    try:
        events = fetch_events(review_ref)
    except (OSError, sqlite3.Error):
        return jsonify({'error': 'Local review log is unavailable'}), 503
    return jsonify({'status': 'completed', 'events': events})


@app.post("/api/v1/detect/image")
def detect_image_route():
    """Local, experimental, whole-image generation analysis only."""
    import hmac
    expected = os.environ.get("BEYONDPIXELS_DEMO_TOKEN", "")
    if not expected:
        return jsonify({"error": "Server demo token is not configured"}), 503
    if not hmac.compare_digest(request.headers.get("Authorization", ""), f"Bearer {expected}"):
        return jsonify({"error": "Unauthorized"}), 401
    uploaded = request.files.get("image")
    if uploaded is None:
        return jsonify({"error": "Send a multipart field named image"}), 400
    data = uploaded.stream.read(MAX_BYTES + 1)
    try:
        open_document_image(data)
        result = detect_image(data, content_already_validated=True)
    except InvalidMedia as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:  # avoid leaking model or uploaded-document internals
        return jsonify({"error": "Local experimental detector is unavailable"}), 503
    deepfake = analyze_deepfake(data)
    return jsonify({"schema_version": "1.0", "image_generation": result, "deepfake": deepfake})


if __name__ == "__main__":
    app.run(host=os.environ.get("BEYONDPIXELS_HOST", "127.0.0.1"), port=8001, debug=False)

"""Honest UI contract for the local research prototype; never assert identity or fraud."""
from __future__ import annotations


from deepfake_service import deepfake_ready
from portrait_face_comparison import DETECTOR, RECOGNIZER
from pathlib import Path
import os


def ui_capabilities() -> dict:
    return {
        "status": "ok",
        "app": "BeyondPixels",
        "research_only": True,
        "input": {"formats": ["JPEG", "PNG"], "max_bytes": 8 * 1024 * 1024},
        "modules": {
            "image_generation": {"available": True, "endpoint": "/api/v1/detect/image", "scope": "whole_image_only"},
            "ocr": {"available": True, "endpoint": "/v1/screen", "scope": "text_and_labelled_fields"},
            "mrz": {"available": True, "scope": "td3_passport_td1_id_card_td2_travel_document_consistency_only"},
            "document_field_consistency": {"available": True, "endpoint": "/v1/screen", "scope": "passport_printed_ocr_vs_td3_mrz_only"},
            "single_image_review": {"available": True, "endpoint": "/v1/screen",
                                    "scope": "localized_printed_vs_mrz_discrepancies_only",
                                    "requires_reference_image": False,
                                    "standalone_forgery_detection": False},
            "tampering_localization": {"available": True, "endpoint": "/v1/screen",
                                      "scope": "aligned_png_reference_pixel_differences_only",
                                      "requires_reference_image": True,
                                      "standalone_forgery_detection": False},
            "visual_artifact_review": {"available": True, "endpoint": "/v1/screen",
                                       "scope": "uncalibrated_jpeg_recompression_diagnostics_only",
                                       "requires_reference_image": False,
                                       "standalone_forgery_detection": False},
            "copy_move_review": {"available": True, "endpoint": "/v1/screen",
                                 "scope": "single_image_repeated_texture_candidates_only",
                                 "requires_reference_image": False,
                                 "standalone_forgery_detection": False},
            "document_portrait_review": {"available": True, "endpoint": "/v1/screen",
                                         "scope": "frontal_face_location_and_uncalibrated_image_quality_only",
                                         "requires_reference_image": False,
                                         "identity_verification": False,
                                         "portrait_replacement_detection": False},
            "face_detection": {"available": deepfake_ready(), "scope": "media_module_only_frontal_faces"},
            "face_verification": {"available": DETECTOR.is_file() and RECOGNIZER.is_file(), "endpoint": "/v1/screen",
                                  "requires_optional_consent_face_photo": True,
                                  "scope": "uncalibrated_face_embedding_similarity_only",
                                  "identity_verification": False},
            "portrait_replacement_review": {"available": DETECTOR.is_file() and RECOGNIZER.is_file(), "endpoint": "/v1/screen",
                                              "requires_optional_consent_face_photo": True,
                                              "scope": "reference_threshold_inconsistency_review_only",
                                              "portrait_replacement_detection": False},
            "standalone_tampering_review": {"available": True, "endpoint": "/v1/screen",
                                             "scope": "bounded_multisignal_triage_without_reference",
                                             "standalone_pixel_forgery_classifier": False},
            "image_similarity": {"available": True, "endpoint": "/v1/screen",
                                 "scope": "opt_in_request_scoped_up_to_four_authorized_reference_images_only",
                                 "persistent_gallery": False, "identity_verification": False},
            "evidence_report": {"available": True, "scope": "status_and_finding_codes_only_no_identity_verdict"},
            "review_audit": {"available": True, "endpoint": "/v1/review",
                             "scope": "local_demo_operator_action_log_no_pii_no_roles_not_tamper_proof"},
            "deepfake": {"available": deepfake_ready(), "endpoint": "/api/v1/detect/image", "scope": "frontal_face_crops_research"},
            "provenance": {"available": True, "endpoint": "/v1/screen",
                           "scope": "embedded_file_metadata_observations_only",
                           "cryptographic_provenance_validation": False},
            "c2pa_verification": {"available": (Path(__file__).resolve().parent / '.venv_c2pa' /
                    ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')).is_file(),
                                  "endpoint": "/v1/screen", "scope": "offline_embedded_manifest_sdk_validation_only",
                                  "remote_fetch": False, "identity_or_document_authentication": False},
        },
        "criterion_selection_supported": False,
        "note": "Feature selection is not implemented; only supported analyses are executed.",
    }

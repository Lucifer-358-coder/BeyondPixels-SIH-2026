# Localhost website implementation brief

**Purpose:** Build an officer-facing *local research demo* for SIH 2026 PS 26188 using the existing Flask API. The website is planned work, not a feature in the 22 September source capture. Keep the Flutter mobile UI as a visual prototype for the presentation; do not imply its screens are the new website or that either is a deployed government system.

Start with [the PS traceability matrix](PS_TRACEABILITY.md), [current status](CURRENT_STATUS.md), [API contract](API.md), and [test plan](TEST_PLAN.md). The backend source, not a slide mockup, is the authority for payload fields and response statuses.

## Navigation and user tasks

| Page or state | Required behavior | PS link |
| --- | --- | --- |
| Home | Lead with **Document Verification** for checkpoint screening. Show **AI Image Detection** as a separate secondary branch. Explain that an officer makes the final decision. | Border-document screening and decision support |
| Local setup | Enter backend URL and demo token for this session; check `/health` and `/v1/capabilities`. Keep token in memory only. Show unavailable models as unavailable. | Reliable screening workflow |
| Document intake | Accept one JPEG/PNG document image, maximum 8 MB. Optional aligned PNG reference, opt-in comparison face photo, and up to four explicitly supplied authorized reference images. Label every optional input and its purpose. | OCR, document checks, tampering, face comparison |
| Document processing | POST to `/v1/screen`; show progress, bounded wait, cancel/return behavior, and clear 400/401/413/503/timeout states. Prevent an accidental duplicate submission. | Faster preliminary review |
| Document result | Show extracted OCR fields as **unverified**, MRZ/checksum/date and printed-field observations, individual tampering indicators, optional face similarity, provenance, and the evidence report. Present `manual_review` or `inconclusive` exactly as returned. | Four PS modules and explainability |
| Officer action | With a valid `review_ref`, allow `reviewed`, `follow_up_required`, or `inconclusive` through `/v1/review`. Explain that this is a local demo action log, without identity data or production access control. | Review trail |
| AI Image Detection | Separate image intake and result using `/api/v1/detect/image`; show whole-image generation and optional per-face manipulation observations separately. | Additional forensic research, not a PS substitute |

The site should work in a desktop browser at localhost. Design a clear, compact officer workflow first; responsive layout can follow. Do not present a website screenshot or AI-generated visual as a working screen until the implemented page is tested.

## Document workflow and response mapping

1. Intake an image. The backend currently has no general `document_type` input or validated passport/visa/licence/permit classifier. A user-selected label is for demo organization only; it must not be sent as a claim of automatic recognition.
2. Call `POST /v1/screen` with `Authorization: Bearer <local token>` and multipart field `image`. Optional field names: `reference_image`, `comparison_photo`, and repeated `authorized_reference_images` (maximum four). This is the same bounded contract used by the Flutter client.
3. Use `ocr.fields` and `ocr.mrz_fields` for extracted text; display `ocr.fields_verified: false` and `ocr.mrz_fields_verified: false` in plain language. Missing, ambiguous or unavailable values stay unknown.
4. Show `document_validation` (MRZ), `document_consistency`, `document_format_review`, `single_image_review`, `visual_artifact_review`, `copy_move_review`, `tampering_localization`, `document_portrait_review`, `face_verification`, `provenance`, `content_credentials`, `image_similarity` and `evidence_report` as **separate observations**. Render each module's own status; do not collapse a diagnostic into “fake passport.”
5. Put `screening_status`, `review_notes`, the backend `disclaimer`, and actionable evidence at the top of the result. The current API returns `manual_review` or `inconclusive`. It does not return a validated 0–100 risk score. A risk-score panel belongs behind a future, explicitly specified and evaluated backend contract.
6. The document route returns `image_generation: not_applicable` and `deepfake: not_implemented`. Do not display these as completed document checks. Any future document-photo integration needs a separately scoped design and validation.

For the PS's “rules and databases” requirement, display local rules that actually ran. Do not show “blacklist clear”, “visa valid”, “database verified” or “identity verified”; no authorized record connector exists in this capture. A future mock adapter should distinguish `match`, `mismatch`, `no_record`, and `unavailable`, and be marked **synthetic demo data**.

## AI Image Detection response mapping

Call `POST /api/v1/detect/image` with multipart `image` and the same local bearer token. Render `image_generation.status`, `decision`, and `ai_generation_score` using the backend's interpretation text. A classifier score is a domain-specific model score, not a probability that a passport is forged. Render `deepfake.status` and per-face observations separately; `unavailable` and `not_assessed` are valid results. This branch must never issue an identity or document-authenticity verdict.

## UI states and guardrails

- Before upload: accepted JPEG/PNG, 8 MB limit, fictional/consented samples only. Check the optional face-photo consent box before sending biometric comparison data.
- During analysis: indicate which branch is running and allow the user to return without promising a completed result. Do not show fabricated progress percentages.
- On result: distinguish `completed`, `not_checked`, `not_applicable`, `not_assessed`, `unavailable`, `review_required`, `manual_review`, and `inconclusive` where returned. Never turn missing evidence into a pass.
- On 401: ask the operator to correct the token. On 413 or invalid media: request a valid smaller image. On 503: show the missing server/model/log capability. On timeout or network failure: report that no result was established; do not automatically retry a sensitive upload.
- Never place tokens in URLs, source code, browser local storage, analytics or logs. Do not persist uploaded documents or facial images in the web frontend. Keep the backend bound to localhost for the demo. The current localhost CORS rule permits `localhost` and `127.0.0.1` origins; do not widen it to `*`.
- No real government-system, role-based access, or travel decision UI is supported by the current backend. Those are deployment requirements, not cosmetic website tasks.

## Definition of done for the website demo

1. Clean-machine startup instructions launch Flask and the site; health/capabilities and token handling work on the same machine.
2. A labelled synthetic readable document shows OCR/MRZ fields and an evidence report. A mismatch/expired sample shows the actual review reason. A blurred sample preserves unknown/inconclusive output.
3. Optional face comparison visibly requires consent and handles missing face models. Document analysis never claims the AI-image classifier proves forgery.
4. The separate AI Image Detection page shows a real completed model result or an honest unavailable state.
5. Invalid file, oversize file, wrong token, backend down and model unavailable each produce a clear, accurate state.
6. Record actual latency and evaluation metrics on a documented test matrix before claiming speed or accuracy in the site or video.
7. A reviewer can perform and retrieve a local review action if the demo log is available; it is explicitly labelled demo-grade.

Suggested build order: connect health and token; implement Document Verification intake/results; add review action; implement AI Image Detection; run the PS sample matrix; then polish visual design. A web framework may be chosen by the team, but no framework choice should change the backend's existing contract or imply unbuilt features.

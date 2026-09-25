# Current status (25 September 2026)

This reflects the **22 September active source capture**, the 21 September backend dependency list, and the 25 September source-based readiness assessment. It is not a live test of the team's current Windows installation.

| Area | Observed | Open work |
| --- | --- | --- |
| UI and API | Flutter screens and Flask routes for two separate branches are present. | End-to-end Windows, Android and Web runs need verification; this source archive omits Flutter platform folders. |
| Localhost website | No website implementation in this source capture; the build brief is documented. | Implement and verify the site against the existing API and PS traceability matrix. |
| OCR | Tesseract path, labelled fields, MRZ extraction and date handling. | Document-class test matrix, field accuracy and degraded-image handling. |
| Document rules | TD3 plus bounded TD1/TD2 consistency; passport printed-field comparison. | Issuer/status checks, broader document rules, false-alarm measurement. |
| Tampering | Several diagnostic indicators and optional reference-image pixel comparison. | Held-out forgery evaluation, photo/text/stamp-specific detection. |
| Face comparison | Optional comparison image and model-dependent similarity output. | Calibrated threshold, consented test pairs, live capture and spoof assessment. |
| AI Image Detection | Research classifier code and abstention path; optional visual/deepfake research services. | Model weights absent from repo; evaluate unseen generators and false positives. Deepfake is not a document or identity verdict. |
| Database checks | Request-scoped comparison with up to four operator-provided images. | Authorized issuer, visa and blacklist integration; no such connector is present here. |
| Risk and audit | Evidence report, review notes and optional local SQLite operator actions. | Specified/calibrated risk score, roles, protected audit, retention policy. |

**Do not repeat older 80-85% completion estimates as measured fact.** A 25 September illustrative evidence rubric awarded roughly 37/100 (~40%) for problem-statement coverage. That is a planning estimate, not measured accuracy, and reflects gaps in both functionality and verification. Verify improvements on the current machine before changing these statements.

## Priority work

1. Make a clean machine run reliable: backend token, health, document and image routes, and actual Flutter UI.
2. Assemble authorized or synthetic passport, visa, ID, licence and permit cases, including blur, expiry, mismatches, altered photos and stamps. Record field accuracy, false alarms, misses and latency.
3. Add mock authorized-record adapter with match, mismatch, no-record and unavailable states; avoid claiming government access.
4. Validate document-specific forgery and optional face comparison on held-out samples; abstain when evidence is insufficient.
5. Define a transparent, reviewable risk indicator and officer workflow, then add appropriate access controls and audit retention.

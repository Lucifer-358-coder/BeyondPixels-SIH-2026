# SIH 2026 PS 26188 — Requirement Map

The problem focuses on screening passports, visas, identity documents, and related travel documents at checkpoints where manual verification may be affected by altered information, manipulated photographs, impersonation attempts, suspicious documents, and high processing volume.

BeyondPixels maps the problem into document-specific verification plus a separate **AI Image and Deepfake Detection** workflow.

| Problem Area | BeyondPixels Response |
| --- | --- |
| Altered or inconsistent personal information | OCR, MRZ parsing, printed-field comparison, and field-consistency checks |
| Expired or suspicious dates | Date and expiry checks |
| Fake or modified document regions | Tampering indicators, copy-move analysis, and visual-anomaly observations |
| Altered document photograph or impersonation | Optional face verification and document-portrait analysis |
| AI-generated imagery | AI Image and Deepfake Detection — AI-image analysis |
| Face manipulation or deepfakes | AI Image and Deepfake Detection — face/deepfake analysis |
| Slow repetitive manual checking | Automated preliminary analysis with explainable evidence |
| Need for officer oversight | Manual-review, inconclusive, and unavailable states rather than automatic travel decisions |
| Future record verification | Architecture for approved government API/database integration |

## Product Structure

### Document Verification

This is the document-focused workflow and includes OCR Extraction, MRZ and consistency checks, Tampering Detection, Face Verification, and other document-review indicators.

### AI Image and Deepfake Detection

This is the second major BeyondPixels workflow and analyzes synthetic and manipulated visual media separately from document-authenticity checks.

The two workflows support the same review process, but one must not be treated as a substitute for the other.

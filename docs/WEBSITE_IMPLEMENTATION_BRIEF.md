# Localhost Operator Dashboard

**Purpose:** provide a larger operator-facing interface for the BeyondPixels prototype while using the existing backend APIs.

The dashboard is intended to demonstrate the real processing pipeline locally. The mobile UI remains a separate compact visual representation for presentation use.

## Main Navigation

| Page / State | Purpose |
| --- | --- |
| Home | Present the two core modules: **Document Verification** and **AI Image and Deepfake Detection** |
| Local Connection | Configure the local backend session and verify backend capability status |
| Document Upload | Upload the document and supported optional comparison inputs |
| Document Result | Show OCR, MRZ, consistency, tampering, face, provenance, and review evidence |
| Review Action | Record a local operator review action where supported |
| AI Image and Deepfake Detection | Upload media and show AI-image and deepfake / face-manipulation observations separately |

## Document Verification Flow

1. Upload a supported image.
2. Send it to `POST /v1/screen`.
3. Show OCR and MRZ values as extracted evidence.
4. Show each document-review module separately.
5. Keep missing or unavailable evidence visible rather than turning it into a pass.
6. Present the backend review state and explanation clearly.
7. Never use an AI-image score as proof that a passport, visa, or identity document is forged.

## AI Image and Deepfake Detection Flow

Use `POST /api/v1/detect/image`.

The interface should separately present:

- AI-image analysis status
- AI-generation model score / decision where available
- forensic indicators
- deepfake / face-manipulation status
- per-face observations where supported
- unavailable / not-assessed states

This branch does not issue a document-authenticity or identity verdict.

## Interface Guardrails

- Use fictional, synthetic, or authorized samples.
- Do not store credentials in the frontend.
- Do not persist uploaded identity documents in browser storage.
- Keep unavailable checks clearly labelled.
- Handle invalid file, oversize file, wrong token, backend-down, and missing-model states clearly.
- Do not show fabricated progress percentages or fake verification claims.
- Keep the final decision with the authorized human reviewer.

## Development Goal

The operator dashboard should make the BeyondPixels workflow easy to understand on a larger screen while keeping all detection and verification logic inside the common backend.

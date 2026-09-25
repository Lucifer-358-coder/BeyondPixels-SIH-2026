# Local API contract

Source: `backend/app.py` in the 22 September capture. Base URL for same-machine demo: `http://127.0.0.1:8001`.

| Route | Method | Purpose |
| --- | --- | --- |
| `/health` | GET | Demo server health, without a claim that every optional model is ready. |
| `/v1/capabilities` | GET | Report bounded module availability and limitations. |
| `/v1/screen` | POST | Document Verification; multipart `image`, optional `reference_image`, comparison photo and up to four authorized reference images per source contract. Requires demo bearer token. |
| `/api/v1/detect/image` | POST | Research AI Image Detection; multipart image and demo bearer token. |
| `/v1/review` | POST | Save optional operator action in local demo log with valid review reference and token. |
| `/v1/review/<review_ref>` | GET | Retrieve local review actions with token. |

Consult the route source and tests before changing multipart field names or using a response field. The token is set in `BEYONDPIXELS_DEMO_TOKEN` on the backend and sent as `Authorization: Bearer <token>`. Never log or commit it. `screening_status` is `manual_review` or `inconclusive`; it is not a travel authorization or a calibrated probability of fraud.

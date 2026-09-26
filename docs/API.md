# Local API Contract

Base URL for the current same-machine prototype: `http://127.0.0.1:8001`

| Route | Method | Purpose |
| --- | --- | --- |
| `/health` | GET | Backend health check. |
| `/v1/capabilities` | GET | Reports available modules and local capability status. |
| `/v1/screen` | POST | **Document Verification**; accepts the document image and supported optional comparison inputs. |
| `/api/v1/detect/image` | POST | **AI Image and Deepfake Detection**; accepts an uploaded image and returns available AI-image / face-manipulation observations. |
| `/v1/review` | POST | Stores an optional operator review action in the local prototype log. |
| `/v1/review/<review_ref>` | GET | Retrieves review actions associated with a local review reference. |

The prototype uses a local bearer token configured through `BEYONDPIXELS_DEMO_TOKEN`.

The token must never be committed to the repository or displayed in logs.

Document screening results are evidence for review. A model score or `screening_status` must not be interpreted as a travel authorization, legal identity decision, or calibrated probability of fraud.

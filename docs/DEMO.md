# BeyondPixels Demonstration

1. Prepare **fictional/synthetic or consented** samples: a readable passport-like example, a mismatched or expired example, a blurred example, and media samples for AI-image and deepfake analysis. Label simulated documents clearly.
2. Start the backend, check `/health` and `/v1/capabilities`, and start the available user interface. Verify the local demo token on both branches.
3. Lead with **Document Verification**: upload the readable sample; show extracted fields, MRZ/date checks and evidence report. Explain which checks actually ran.
4. Upload the mismatch/expiry sample; show the exact inconsistency and manual-review reason. Upload the blurred sample; show uncertainty rather than a genuine/fake verdict.
5. If local face models and a consented comparison photo are available, show the optional similarity observation and state its limitations.
6. Show **AI Image and Deepfake Detection** separately. Demonstrate AI-generated image screening and, when the local deepfake model is available, face-manipulation analysis. Only claim results from analyses that actually completed.
7. Explain the current development scope: authorized-record checks, broader document-specific validation, additional tamper testing, model evaluation, and deployment hardening remain future work.

Record actual timings and test metrics before putting numbers in a slide or video. The mobile UI may be used as an AI-assisted visual representation of the intended interface, while the localhost operator dashboard is used to demonstrate the working processing pipeline. Do not present design-only screens as measured model output.

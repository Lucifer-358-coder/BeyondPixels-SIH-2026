# Judge demo runbook

1. Prepare **fictional/synthetic or consented** samples: a readable passport-like example, a mismatched or expired example, a blurred example, and a media sample. Label simulated documents clearly.
2. Start the backend, check `/health` and `/v1/capabilities`, and start the Flutter Windows UI. Verify the local demo token on both branches.
3. Lead with **Document Verification**: upload the readable sample; show extracted fields, MRZ/date checks and evidence report. Explain which checks actually ran.
4. Upload the mismatch/expiry sample; show the exact inconsistency and manual-review reason. Upload the blurred sample; show uncertainty rather than a genuine/fake verdict.
5. If local face models and a consented comparison photo are available, show the optional similarity observation. State its limitations.
6. Show **AI Image Detection** separately. Only claim a model result if the relevant model is present and the analysis actually completed. Deepfake is experimental and distinct from face verification.
7. Explain what remains: authorized-record checks, validated risk score, document-specific tamper tests, broader formats, clean-machine and platform testing.

Record actual timings and test metrics before putting numbers in a slide or video. The UI is a prototype visual representation; any future localhost website should be described as such until built and tested. Do not present fabricated screenshots as real output.

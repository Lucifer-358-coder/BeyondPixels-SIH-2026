# Verification Plan

## End-to-End Local Run

- Start the Flask backend with a fresh local demo token.
- Verify `/health` and `/v1/capabilities`.
- Test Document Verification with valid, degraded, mismatched, and invalid inputs.
- Test AI Image and Deepfake Detection with authentic photos, AI-generated images, and appropriate deepfake samples.
- Verify clear behavior for missing models, invalid media, authentication errors, and backend failures.
- Record only measured results from repeatable test runs.

## Document Test Matrix

Use fictional, synthetic, or consented samples covering document classes relevant to the project.

Where applicable, include:

- clear image
- blur
- crop
- compression
- expired date
- field mismatch
- altered photograph
- text/date manipulation
- stamp or region manipulation

Track field accuracy, false positives, false negatives, abstentions, and latency.

## AI Image and Deepfake Evaluation

For AI-image analysis, track:

- dataset source and license
- sample counts
- train / validation / test separation
- duplicate screening
- model version / hash
- real-photo false positives
- unseen-generator performance
- compression and resizing robustness

For deepfake analysis, evaluate face manipulation separately from face identity similarity.

## Reporting

Do not copy illustrative percentages into the public project documentation.

Accuracy, speed, or detection-rate claims should be added only after they have been measured on a documented test set.

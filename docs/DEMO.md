# BeyondPixels Demonstration

The demonstration focuses on the two core BeyondPixels workflows and the explainable evidence produced for human review.

## Document Verification

1. Upload a fictional, synthetic, or otherwise authorized document sample.
2. Run OCR and MRZ extraction where applicable.
3. Show printed-field and MRZ consistency observations.
4. Display date and expiry checks.
5. Show available tampering and forensic-image indicators.
6. If the required local face model and consented comparison image are available, show face-similarity observations.
7. Present the evidence summary and any manual-review reason.

A degraded or intentionally altered sample can be used to demonstrate how the system handles inconsistency or uncertainty.

## AI Image and Deepfake Detection

1. Upload a normal photographic image.
2. Run AI-image analysis and show the available forensic and learned-model indicators.
3. Upload an AI-generated test image and show the corresponding analysis.
4. When the deepfake model is available, use a suitable face image to demonstrate face-manipulation analysis.
5. Keep AI-image and deepfake results separate and explain what each result means.

## Interface

The current prototype uses the Flutter mobile interface as the visual client for the BeyondPixels workflow.

## Result Philosophy

BeyondPixels should not force uncertain evidence into an absolute verdict.

Depending on the evidence, the interface can communicate states such as:

- checks completed
- suspicious indicators found
- manual review required
- inconclusive
- unavailable

The authorized human reviewer remains responsible for the final decision.

# BeyondPixels Demonstration

The current demonstration focuses on the core BeyondPixels processing workflow.

## Document Verification

1. Upload a fictional, synthetic, or otherwise authorized document sample.
2. Run OCR and MRZ extraction where applicable.
3. Show printed-field and MRZ consistency observations.
4. Display date / expiry checks.
5. Show available tampering and forensic-image indicators.
6. If the required local face model and consented comparison image are available, show face-similarity observations.
7. Present the final evidence summary and any manual-review reason.

A second degraded or intentionally altered sample can be used to demonstrate how the system handles inconsistency or uncertainty.

## AI Image and Deepfake Detection

1. Upload a normal photographic image.
2. Run AI-image analysis and show the available forensic / learned-model indicators.
3. Upload an AI-generated test image and show the corresponding analysis.
4. When the deepfake model is available, use a suitable face image to demonstrate face-manipulation analysis.
5. Keep AI-image and deepfake results separate and explain what each result means.

## Current Interface Status

The Flutter mobile interface is the current prototype interface and visual representation.

Website development has **not started yet**. When the web interface is implemented, this document will be updated with the real workflow.

## Result Philosophy

BeyondPixels should not force uncertain evidence into an absolute verdict.

Depending on the evidence, the interface can communicate states such as:

- checks completed
- suspicious indicators found
- manual review required
- inconclusive
- unavailable

The authorized human reviewer remains responsible for the final decision.

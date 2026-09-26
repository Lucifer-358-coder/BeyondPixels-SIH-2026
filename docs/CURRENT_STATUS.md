# Current Status — 27 September 2026

BeyondPixels is under active development. This repository currently documents the core platform and prototype capabilities.

| Area | Current State | Ongoing Work |
| --- | --- | --- |
| Backend | Flask API with separate document and media-analysis routes. | Continued reliability, validation, and integration testing. |
| Mobile UI | Flutter-based mobile interface prototype available as a visual representation of the workflow. | Keep UI aligned with backend capabilities and presentation design. |
| Website | **Not started yet.** | Website work will be added and documented only after development begins. |
| OCR / MRZ | OCR extraction, MRZ parsing, date handling, and consistency-oriented logic are present. | Broader document-class testing and degraded-image evaluation. |
| Document Verification | Field consistency, date checks, image-forensic indicators, and optional face comparison are available in the prototype pipeline. | Broader rule packs, document-specific validation, and measured evaluation. |
| Tampering Analysis | Multiple visual and forensic indicators are available. | Larger held-out evaluation for photo, text, date, and stamp manipulation. |
| Face Verification | Optional comparison workflow using local models where available. | Threshold calibration, spoof/quality handling, and broader evaluation. |
| AI Image and Deepfake Detection | Separate experimental pipeline for AI-image screening and face/deepfake analysis. | Evaluation on unseen generators, compression/resizing, real-photo false alarms, and wider deepfake samples. |
| Government Record Integration | Architecture allows future authorized integrations. | No protected passport, visa, blacklist, watchlist, or immigration connector is included in the public prototype. |
| Explainability / Review | Per-check observations and manual-review states are part of the prototype approach. | Continued validation and future deployment-grade audit controls. |

## Current Priorities

1. Keep **Document Verification** and **AI Image and Deepfake Detection** clearly separated.
2. Improve backend reliability and controlled testing.
3. Expand evaluation across readable, degraded, altered, AI-generated, and deepfake samples.
4. Record measured accuracy, false positives, false negatives, abstentions, and latency only after repeatable evaluation.
5. Keep all public claims aligned with demonstrated functionality.

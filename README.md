# BeyondPixels

**Research prototype for SIH 2026 problem statement 26188: identity and travel document screening at border checkpoints.**

BeyondPixels has two user-facing branches:

1. **Document Verification**: OCR, MRZ and printed-field checks, limited image-forensic observations, optional face comparison, and an evidence report for officer review. The PS calls its corresponding module *Document Validation*.
2. **AI Image Detection**: separate experimental screening for whole-image generation, with optional face-manipulation analysis when the local research model is installed.

The goal is decision support for a human reviewer. Current output cannot certify document authenticity, establish a person's identity, or authorize/refuse travel. See [current status](docs/CURRENT_STATUS.md) before presenting capabilities.

## Problem statement mapping

| PS requirement | Present source and limitation |
| --- | --- |
| OCR Extraction | Tesseract-based OCR and some labelled fields; real multi-format and degraded-capture coverage is unmeasured. |
| Document Validation | **Document Verification** performs TD3 passport and bounded TD1/TD2 MRZ checks, date and limited printed-field comparisons. No issuer confirmation. |
| Tampering Detection | Field discrepancies, image artifacts, copy-move candidates and optional aligned reference comparison are review indicators. No validated general forgery or visa-stamp classifier. |
| Face Verification | Optional document-photo versus supplied comparison-photo embedding similarity if local models are installed. No calibrated identity verdict or live capture. |
| Rules and databases | Some local rules exist. There is no authorized passport, visa, watchlist or blacklist connector in this snapshot. |
| Risk score and review trail | Evidence statuses and optional local operator-action log exist. No calibrated unified risk score or production audit trail. |

The separate AI Image Detection branch is extra research work. Its scores do not prove whether a document is genuine.

## Repository contents

- `backend/`: Flask API, OCR/document checks, experimental media analysis, tests and research scripts.
- `frontend/`: Flutter source and unit tests. The captured source lacks generated platform folders; see setup.
- `docs/`: architecture, setup, API, model/data provenance, demo, status and roadmap.
- `CONTRIBUTING.md`: team workflow and review rules.

The source snapshot is from **22 September 2026**. The 25 September assessment is a source-based evaluation, not a verified live build. Machine-specific launcher, model weights, training images, identity documents, secrets, virtual environments and build binaries are intentionally excluded. A copied backend dependency list is from the 21 September package; revalidate it with the active machine before a release.

## Quick start

Use [docs/SETUP.md](docs/SETUP.md). In brief: install Python dependencies and Tesseract, set a fresh local demo token, start Flask on `127.0.0.1:8001`, generate missing Flutter platform scaffolding, then run Flutter from `frontend/`. The AI image and face model paths require separately licensed, verified local artifacts. Missing artifacts should be shown as unavailable, not silently represented as working.

## Working agreement

For a new team member, start with [architecture](docs/ARCHITECTURE.md), [current status](docs/CURRENT_STATUS.md), and [demo guide](docs/DEMO.md). Develop on a branch, use a pull request into `main`, and attach test evidence. Do not upload real identity records or tokens even to this private repository.

**License:** No project-wide reuse license is granted yet. Review third-party datasets, checkpoints and code separately before distribution or deployment.

# BeyondPixels

**AI-Assisted Document Verification & AI Image and Deepfake Detection Platform**  
**Smart India Hackathon 2026 — Problem Statement 26188**

BeyondPixels is an AI-assisted identity and document screening platform designed to support faster, more consistent, and explainable verification at border checkpoints, airports, transport hubs, and other authorized government facilities.

The platform has **two separate core modules**:

1. **Document Verification**
2. **AI Image and Deepfake Detection**

BeyondPixels is designed as a **decision-support system**. It analyzes available evidence, highlights inconsistencies or suspicious indicators, and supports manual review. The final decision remains with the authorized human officer.

## Problem We Address

Identity and travel-document screening can involve:

- altered or forged passports, visas, and identity documents
- modified dates or personal information
- manipulated document photographs
- identity impersonation
- inconsistent printed and machine-readable information
- AI-generated images
- deepfake or face-manipulated media
- high document volumes that increase manual review time

Rather than relying on a single score, BeyondPixels combines multiple checks and presents the findings as explainable evidence.

## 1. Document Verification

The Document Verification workflow focuses on document-specific evidence, including:

- OCR-based text extraction
- MRZ parsing and validation
- printed-field and MRZ consistency checks
- date and expiry checks
- metadata and provenance observations
- tampering indicators
- copy-move and visual-anomaly analysis
- optional face verification
- structured evidence for manual review

The system is designed to support outcomes such as **checks completed**, **suspicious**, **inconclusive**, **unavailable**, or **manual review required** rather than forcing every case into a simple real/fake answer.

## 2. AI Image and Deepfake Detection

This is a separate workflow for synthetic and manipulated visual media.

It can include:

- AI-generated image screening
- learned visual-model analysis
- frequency, noise, texture, and compression indicators
- deepfake / face-manipulation analysis
- explainable forensic observations
- inconclusive or unavailable states when evidence is insufficient

AI-image and deepfake outputs are treated as **forensic indicators**. They are not used as standalone proof that an identity document is genuine or fraudulent.

## High-Level Architecture

```text
                     BEYONDPIXELS
                          |
                 Common Backend / APIs
                          |
        +-----------------+----------------------+
        |                                        |
Document Verification            AI Image and Deepfake Detection
        |                                        |
 OCR / MRZ / Face /              AI Image / Deepfake /
 Consistency / Tampering         Forensic Signals / XAI
        |                                        |
        +-----------------+----------------------+
                          |
                  Explainable Result
                          |
                   Human Reviewer
```

## Current Prototype Scope

Current development includes:

- Python / Flask backend
- OCR and MRZ-oriented document checks
- document consistency rules
- tampering and forensic-image indicators
- optional face comparison
- AI-generated image detection pipeline
- deepfake / face-manipulation pipeline
- explainable result handling
- Flutter mobile interface prototype
- **public Next.js website foundation**

## Website Development Updates

The public repository now also shows **how the website is being built**, not only finished changes.

| Date & Time | Status | Update |
| --- | --- | --- |
| 29 September 2026, 11:58 PM IST | **Implemented / Build Verified** | Day 1 website foundation completed: AI Cybersecurity SaaS direction frozen, operator-first UX defined, Next.js/React/Tailwind frontend created, landing page implemented, and production build verified through GitHub Actions. |
| 27 September 2026 | Planned | Public evaluator-facing repository prepared. Website development had not started yet. |

For detailed website progress, see [Website Updates](docs/WEBSITE_UPDATES.md).  
For the current Day 1 build record, see [Website Day 1 Build](docs/WEBSITE_DAY_1_BUILD.md).  
The source is available under [website/](website/).

## Website UI Direction

**Frozen direction:** AI Cybersecurity SaaS Website

The website is intentionally designed to avoid:

- conventional government-portal styling
- generic corporate/admin dashboard styling
- overloaded hacker/gaming visuals

The operator experience follows:

**Upload → Analyze → Result → Evidence → Human Review**

Complex backend processing remains hidden by default while actionable results and explainable evidence remain visible.

## Technology Overview

- **Backend:** Python, Flask
- **Document Processing:** OCR, MRZ parsing, consistency and rule checks
- **Computer Vision:** image forensics, face analysis, tampering indicators
- **AI/ML:** AI-image and deepfake detection models
- **Model Execution:** Python and ONNX-based pipelines where applicable
- **Mobile Frontend:** Flutter prototype
- **Web Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Website CI:** GitHub Actions production-build verification
- **Explainability:** per-check observations and review-oriented outputs

## Responsible Use and Privacy

BeyondPixels is intended to be demonstrated using fictional, synthetic, or appropriately authorized samples.

This public repository does not contain real identity documents, private biometric datasets, API tokens, protected government endpoints, confidential records, or restricted model files that cannot legally be redistributed.

When evidence is incomplete, the system should report **inconclusive**, **unavailable**, or **manual review required** instead of presenting an unsupported conclusion.

## Future Deployment Direction

A future authorized deployment could place the BeyondPixels processing layer inside secure or on-premise infrastructure and connect it to approved government services through controlled APIs or integration layers.

Possible future integrations may include authorized passport, visa, identity, blacklist, watchlist, or immigration-record services. The current prototype does **not** claim access to those protected systems.

## Repository Purpose

This repository provides the public technical overview and visible development history of BeyondPixels for SIH 2026, including the project scope, architecture, website build progress, status, testing approach, and supporting documentation.

## Project

**Name:** BeyondPixels  
**SIH 2026 Problem Statement:** 26188  
**Primary Modules:** Document Verification + AI Image and Deepfake Detection

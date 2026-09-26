# Architecture and Scope

```mermaid
flowchart TB
    UI1[Operator Web Dashboard] --> API[BeyondPixels Backend / APIs]
    UI2[Mobile UI Representation] --> API
    API --> DV[Document Verification]
    API --> AIDF[AI Image and Deepfake Detection]
    DV --> OCR[OCR and MRZ]
    DV --> DOC[Consistency / Tampering / Face Checks]
    AIDF --> AI[AI Image Analysis]
    AIDF --> DF[Deepfake / Face-Manipulation Analysis]
    OCR --> REV[Explainable Result]
    DOC --> REV
    AI --> REV
    DF --> REV
    REV --> HUMAN[Authorized Human Reviewer]
```

## Document Verification

Document Verification covers the document-focused workflow, including OCR extraction, MRZ processing, printed-field consistency, date checks, tampering indicators, and optional face comparison.

The individual checks remain separately explainable. They do not collapse into an unsupported single “fake document” classifier.

## AI Image and Deepfake Detection

This is a separate media-analysis branch.

The current backend exposes image-analysis services that can provide whole-image AI-generation observations and, when the relevant local model is available, deepfake / face-manipulation observations.

This branch is intentionally separate from Document Verification because an AI-generated-image score is not equivalent to document-authenticity verification.

## Human Review Layer

BeyondPixels is designed to provide evidence to the reviewer.

The reviewer should be able to see:

- which checks completed
- which checks were unavailable
- what information was extracted
- which inconsistencies were found
- which forensic indicators contributed to the result
- whether further manual review is recommended

## Deployment Direction

The current prototype runs locally.

A future authorized deployment can place the processing layer on secure or on-premise infrastructure while allowing approved clients at checkpoints or government facilities to access it through controlled APIs.

Protected government records should be accessed only through authorized integration services with authentication, authorization, logging, and appropriate data-handling controls.

## Data Handling

Only fictional, synthetic, or properly authorized samples should be used in demonstrations and testing.

Credentials, production tokens, real identity records, private biometric data, restricted datasets, and protected endpoints must remain outside the public repository.

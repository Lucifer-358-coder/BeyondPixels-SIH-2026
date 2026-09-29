# BeyondPixels Website Design System — Day 1

## Frozen Product Direction

**AI Cybersecurity SaaS Website**

This is the fixed visual direction unless the project owner explicitly changes it.

## Experience Goal

The website should feel like a premium security-intelligence product rather than:
- a conventional government portal
- a generic business/admin dashboard
- a gaming or hacker-template interface

The normal operator experience must remain simple:

**Upload → Analyze → Result → Evidence → Human Review**

Backend implementation details stay hidden by default. Technical details may be exposed progressively for expert/judge review.

## Core Information Hierarchy

### Level 1 — Operator Summary
Show:
- selected workflow
- analysis status
- overall evidence state
- confidence only when supported by the backend
- primary observations
- recommended next action

### Level 2 — Evidence
Show on demand:
- OCR/extracted fields
- MRZ results
- consistency issues
- document validity observations
- tampering/localization evidence
- face comparison where supported
- AI-image observations
- deepfake/face-manipulation observations
- provenance/metadata observations

### Level 3 — Expert Detail
Optional:
- module/model availability
- model/version identifiers where appropriate
- processing/inference timing
- raw per-module scores when they are meaningful
- technical reasons for unavailable/inconclusive checks

## Brand Tokens

| Token | Purpose | Value |
| --- | --- | --- |
| Background | Primary canvas | `#060913` |
| Soft background | Secondary canvas | `#0A1020` |
| Surface | Cards/panels | dark navy/slate |
| Primary accent | Active intelligence / interaction | `#38BDF8` |
| Primary blue | CTA / data emphasis | `#3B82F6` |
| Secondary accent | Depth / AI layer | `#6366F1` |
| Success | Completed/available | `#5EE7B0` |
| Warning | Review attention | `#FBBF24` |
| Risk | Suspicious evidence | `#FB7185` |
| Main text | Primary copy | `#F8FAFC` |
| Muted text | Secondary copy | `#94A3B8` |

## Visual Rules

- Dark blue-black surfaces, not pure black.
- Restrained cyan/indigo glow; no rainbow neon.
- Strong typography and spacious layout.
- Thin borders and layered depth instead of heavy shadows.
- Motion must communicate analysis/status, not decorate.
- Result meaning must never depend on color alone.
- Avoid fake progress percentages and fabricated scores.
- Keep Document Verification and AI Image and Deepfake Detection visually distinct.

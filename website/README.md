# BeyondPixels Website

This directory contains the evaluator-visible BeyondPixels website build.

## Current direction

**AI Cybersecurity SaaS Website**

The interface is intentionally designed to avoid both conventional government-portal styling and generic office/admin dashboards.

## Day 1 scope

- Next.js + React + Tailwind CSS foundation
- responsive landing-page shell
- AI Cybersecurity SaaS visual system
- separate workflow presentation for:
  - Document Verification
  - AI Image and Deepfake Detection
- operator-first UX principle:
  **Upload → Analyze → Result → Evidence → Human Review**

## Run locally

```bash
cd website
npm install
npm run dev
```

## Important status

The current Day 1 website is a frontend foundation. Backend API integration, upload workflows, result pages, and end-to-end verification are not yet claimed as complete.

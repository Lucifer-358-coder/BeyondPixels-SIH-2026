# Future judge-facing repository plan

Create a separate judge-facing repository **after** the website and demo are verified. This private team repository remains the development source of truth. Do not create a second codebase that silently diverges; copy only a reviewed release snapshot with a recorded commit SHA.

## Proposed contents

- A concise PS 26188 overview and requirement-to-demonstration table, using [PS_TRACEABILITY.md](PS_TRACEABILITY.md) as the source.
- A clean, reproducible localhost demo: only the code, dependencies and synthetic fixtures actually needed to run it. If model distribution rights are unclear, provide approved download instructions and an unavailable-state demo instead of uploading weights.
- `README.md` with exact Windows setup, known runtime requirements and a tested one-command or short-command launch path.
- A short demo video showing actual app output, a readable document, a mismatch and an inconclusive case, then the separate AI Image Detection branch. Any design-only mobile mockup must be labelled as visual representation.
- A small evaluation table with real sample provenance, confusion counts, latency and limitations. Leave metrics unfilled until measured; do not copy illustrative scores.
- Security and data-handling notes: no real IDs, faces, tokens, private credentials, raw datasets, or government endpoints.

## Release gate

Before sharing judge access, check the release on a clean machine; verify both routes, dependencies/models, sample labels, links and video; run a secret and personal-data scan; confirm the repo's intended visibility and collaborator list. Freeze a tagged snapshot and make any later corrections traceable to the team repo. This is a plan, not a claim that a judge repository or website already exists.

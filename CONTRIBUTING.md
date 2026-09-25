# Team workflow

1. Clone the private repo after accepting the GitHub collaborator invitation.
2. Create a branch from `main` (for example `feature/ocr-improvements`). Open a pull request with a concise description, test commands and sample output without identity data.
3. Keep `main` suitable for the judge demo. Rehearse on the actual Windows installation before promoting a release claim.
4. Update `docs/CURRENT_STATUS.md`, `docs/API.md` and `docs/MODEL_DATA.md` when behavior, contracts, datasets or checkpoints change.
5. Use only synthetic or explicitly consented images in tests; anonymize logs. Never commit `.env`, token stores, private IDs, biometric records, raw datasets, model binaries or virtual environments. If a secret is accidentally committed, remove it from Git history and rotate it.
6. Do not imply that a model score proves fraud, identity, a real government record match or a risk probability. Include an inconclusive/manual-review path.

No general open-source license has been selected. Private access is for collaboration; it is not permission to redistribute third-party models or data.

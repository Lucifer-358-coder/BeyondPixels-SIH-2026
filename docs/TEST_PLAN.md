# Verification plan

## Clean local run

- Start Flask with a fresh local token; verify `/health` and `/v1/capabilities`.
- Test both branches with good input, invalid format, oversize input and wrong/missing token.
- Run Flutter Windows UI against this server; check error messages and unavailable-model cases.
- Repeat on Android and Web only when their endpoints, builds and security behavior are configured and tested.

## Document matrix

Use synthetic or consented examples for passport, visa, national ID, driving licence and permit. For each class include clear, blurry, cropped, expired, field mismatch, photo edit and stamp edit examples as applicable. Keep a held-out set separate from development samples. Record actual field precision/recall, false positives, false negatives, abstentions and latency by class. Do not infer generalized accuracy from unit tests or tiny synthetic samples.

## Media models

Keep data source, license, sample counts, duplicate screening, train/validation/test splits and exact model hashes. Evaluate unseen generators, compression, resizing and real-photo false alarms for AI Image Detection. Evaluate face manipulation separately from face identity similarity. A demo video should show the exact application output, including inconclusive/unavailable states.

## Source snapshot caveat

The captured repository does not ship models or most test fixtures. Python syntax compilation passed in the packaging environment on 25 September 2026. Pytest was unavailable there, so no test-suite pass is asserted. Validate on the team's actual machine before recording results here.

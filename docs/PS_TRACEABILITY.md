# PS 26188 traceability for product and website

This matrix keeps the site and future judge material tied to the user-provided PS. **Observed** means present in the 22 September source capture, not validated on today's Windows installation. **Planned** means a requirement or proposed implementation with no verified working result in this repository.

| PS problem or expected module | Website evidence to show | Source status | Completion evidence needed |
| --- | --- | --- | --- |
| Fake passports, visas and IDs | Document Verification intake and structured observations | Partial OCR/MRZ/rules observed; issuer authenticity not checked | Synthetic/consented cases per document class, exact rules and error rates |
| OCR Extraction | Extracted labelled fields with source and uncertainty | Observed, uneven format coverage | Field accuracy on held-out clear and degraded samples |
| Document Validation in PS | Product label **Document Verification**; MRZ, dates and printed-field consistency | Bounded TD3/TD1/TD2 and passport comparisons observed | Document-specific rule packs and issuer validation |
| Tampering Detection | Show each image/field diagnostic and disputed region, when available | Indicators observed; no validated general forgery or stamp detector | Labelled photo, text/date and stamp edits; measured false alarms/misses |
| Face Verification | Optional, consented document-versus-comparison-photo similarity | Model-dependent, uncalibrated observation | Paired-person evaluation, threshold, poor-quality abstention and spoof review |
| Rules and database validation | Separate local rule result from record-lookup state | Local rules partial; authorized passport/visa/watchlist connector absent | Synthetic mock adapter for demo; authorized integration only in deployment |
| Expired/blacklisted | Date finding, and a separate future record-status state | Some expiry checks; blacklist check absent | Expired cases and authorized/mock record responses |
| Multiple identities | Request-scoped comparison with supplied reference images | Up to four opt-in references; no persistent identity search | Authorized identity data design and evaluation before claiming detection |
| Risk score | Explanations and officer review; reserve clearly labelled future risk slot | `manual_review` / `inconclusive`; no calibrated unified score | Defined factors, thresholds, missing-evidence behavior and calibration |
| Faster screening | Timed end-to-end demo from upload to report | No measured throughput | Repeatable latency table versus manual baseline |
| Digital trail | Local operator action and report reference | Demo SQLite action log; no protected audit or roles | Access control, retention, tamper resistance and review export |
| AI Image Detection | Separate research page, related to synthetic visual evidence | Separate endpoint with optional model dependencies | Licensed model/data provenance and held-out/unseen-generator results |

**Slide and website rule:** Lead with the document-screening PS; show the four PS modules, then mention the separate AI Image Detection branch as additional research. Do not present a synthetic image score as document validation or an uncalibrated similarity as verified identity. A human officer remains the decision-maker.

**Supported input wording:** The PS lists passport, visa, national ID, driving licence and permit. The current generic image upload accepts JPEG/PNG, but specialized verification of every listed type is **not** demonstrated. Label document-type coverage per evaluated class, not per upload capability.

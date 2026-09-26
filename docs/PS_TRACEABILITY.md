# PS 26188 Traceability

This matrix keeps the BeyondPixels documentation and demonstrations tied to the problem statement. **Observed** means present in the available project source and prototype. **Planned** means a requirement or proposed implementation that is not yet verified as a working production feature.

| PS problem or expected module | BeyondPixels evidence | Current status | Completion evidence needed |
| --- | --- | --- | --- |
| Fake passports, visas and IDs | Document Verification intake and structured observations | Partial OCR/MRZ/rules implemented; issuer authenticity is not checked | Synthetic/consented cases per document class, exact rules and measured error rates |
| OCR Extraction | Extracted labelled fields with source and uncertainty | Implemented with uneven format coverage | Field accuracy on held-out clear and degraded samples |
| Document Validation in PS | Product label **Document Verification**; MRZ, dates and printed-field consistency | Bounded TD3/TD1/TD2 and passport comparisons implemented | Document-specific rule packs and authorized issuer validation |
| Tampering Detection | Image/field diagnostics and suspicious-region indicators where available | Indicators implemented; no claim of universal forgery or stamp detection | Labelled photo, text/date and stamp edits; measured false alarms/misses |
| Face Verification | Optional, consented document-versus-comparison-photo similarity | Model-dependent similarity observation | Paired-person evaluation, calibrated threshold, poor-quality abstention and spoof review |
| Rules and database validation | Local rule result separated from external record-lookup state | Local rules partial; protected government connectors are not available in the prototype | Synthetic/mock adapter for demonstration; authorized integration only in deployment |
| Expired/blacklisted | Date finding and separate future record-status state | Some expiry checks implemented; blacklist lookup absent | Expired cases and authorized/mock record responses |
| Multiple identities | Request-scoped comparison with supplied reference images | Limited opt-in reference comparison; no persistent identity search | Authorized identity-data design and evaluation before claiming detection |
| Risk score | Explanations and human review rather than unsupported certainty | Manual-review / inconclusive paths used; no calibrated unified risk score | Defined factors, thresholds, missing-evidence behavior and calibration |
| Faster screening | Timed end-to-end demonstration from upload to report | Performance measurement is still being expanded | Repeatable latency table against a defined baseline |
| Digital trail | Local operator action and report reference | Prototype logging only; not a production audit system | Access control, retention, tamper resistance and review export |
| AI Image and Deepfake Detection | Separate branch for AI-generated image screening and deepfake/face-manipulation analysis | Experimental model pipelines with local dependencies | Licensed model/data provenance and held-out/unseen-generator and deepfake evaluation |

**Presentation rule:** Lead with the document-screening problem statement and its verification modules, then present **AI Image and Deepfake Detection** as the second major BeyondPixels branch. Do not present an AI/deepfake score as proof of document authenticity or an uncalibrated face similarity score as verified identity. A human officer remains the decision-maker.

**Supported input wording:** The problem statement covers passports, visas and identity/travel documents. Generic image upload does not by itself mean every document type has specialized verification. Coverage should be claimed only for document classes that have actually been evaluated.

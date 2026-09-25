# SIH 2026 PS 26188: requirement map

The user-provided problem statement describes border-checkpoint screening of passports, visas, national identity cards, driving licences, permits and travel authorizations. It asks for OCR extraction, document validation against standards/rules and databases, tampering detection, face verification, a risk score, faster officer decisions and an investigation trail.

| Border problem | Relevant PS function | BeyondPixels evidence today |
| --- | --- | --- |
| Changed DOB, expired document | OCR + document rules | Some date/field/MRZ comparisons; no issuer status check. |
| Fake passport or visa | Standards, database and forgery checks | Some consistency indicators; cannot verify issuer authenticity. |
| Altered photo or identity impersonation | Tampering + face verification | Optional photo similarity and visual observations; uncalibrated and no live capture. |
| Visa stamp forgery | Tampering detection | No validated dedicated stamp detector. |
| Blacklisted or lost document | Authorized record checks | No connected status/watchlist system. |
| Multiple identities | Authorized identity records | Up to four supplied images can be compared within one request; no identity database. |
| Slow manual processing | Automated preliminary checks | No measured end-to-end throughput yet. |

The four named PS modules are **OCR Extraction**, **Document Validation** (called **Document Verification** in the product), **Tampering Detection**, and **Face Verification**. A fifth, separate product branch named **AI Image Detection** is experimental additional work. It cannot replace missing document or government-data capabilities.

The official PS title, registered team name/ID, and submission rules should be copied verbatim from the SIH portal by the team before using them in the final deck. Prior copies of slide material used inconsistent titles and estimates.

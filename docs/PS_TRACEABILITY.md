# PS 26188 Traceability

This matrix keeps the BeyondPixels implementation and documentation aligned with the problem statement.

| Requirement / Problem | BeyondPixels Evidence | Current Scope |
| --- | --- | --- |
| OCR Extraction | OCR fields and MRZ extraction | Implemented in prototype; broader accuracy evaluation is ongoing |
| Document Verification | MRZ, dates, field consistency, document review indicators | Implemented in bounded form; issuer authenticity requires authorized external services |
| Tampering Detection | Visual artifacts, copy-move and other forensic indicators | Prototype indicators available; broader forgery evaluation ongoing |
| Face Verification | Optional document-photo versus comparison-photo similarity | Model-dependent; treated as a similarity observation rather than an identity verdict |
| Rules / Database Validation | Local rules plus future integration layer | Protected government connectors are not part of the public prototype |
| Expired / Suspicious Documents | Date checks and review evidence | Local date logic present; official status checks require authorized integration |
| Multiple Identities / Impersonation | Face comparison and future authorized record checks | No persistent identity database in the public prototype |
| Faster Screening | Automated preliminary analysis | End-to-end performance measurement is being expanded |
| Review Trail | Local review references / actions | Prototype-level logging; production audit controls remain future work |
| AI Image and Deepfake Detection | Separate image-analysis route and media-analysis models | Experimental pipeline; broader unseen-generator and deepfake evaluation ongoing |

**Important:** AI-image or deepfake analysis must not be presented as proof of document authenticity, and face similarity must not be presented as verified identity. BeyondPixels is a decision-support platform with human oversight.

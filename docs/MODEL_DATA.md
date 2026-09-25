# Models and data provenance

The repository intentionally contains **no model weights, training dataset, identity images or biometric records**. An optional model should only be installed after its source, exact version/hash, license, intended use and evaluation set are reviewed. Never load a `.pkl` from an untrusted source.

| Component | Source evidence | Local dependency | Limitation |
| --- | --- | --- | --- |
| Whole-image classifier | `image_detector.py` expects a manifest and a CIFAKE-trained SVM; `experiments/` contains training/evaluation scripts. | `backend/models/beyondpixels_cifake_baseline.json` and `.pkl` from team's verified build. | Narrow CIFAKE domain, abstention thresholds; not document-authenticity proof. |
| Optional visual model | `image_detector.py` checks `bp_visual_candidate_manifest.json` and `bp_visual_low_quality.onnx` plus a worker path. | Verified manifest, weights and isolated runtime. | Source snapshot does not contain weights or a portable environment. |
| Experimental deepfake | `deepfake_service.py` credits `Xicor9/efficientnet-b0-ffpp-c23` and FaceForensics++ C23. | `deepfake_ffpp_c23.pth`, compatible isolated environment. | Checkpoint's own description restricts use to academic/research work; not validated real-world forensics. |
| Face comparison | `portrait_face_comparison.py` expects local face detector and recognizer ONNX files. | Approved face models and OpenCV support. | Similarity is uncalibrated; no identity conclusion. |
| OCR and provenance | Tesseract and optional offline C2PA worker. | Tesseract executable; optional separate C2PA runtime. | OCR can err; provenance availability does not prove authenticity. |

Before uploading any future artifact, document dataset/model title, source URL, license, version/hash, split by identity/source generator, duplicate handling, class counts, thresholds, false positives/negatives, unseen-source tests and latency. Do not commit a model simply because it fits GitHub's size limit or the repository is private.

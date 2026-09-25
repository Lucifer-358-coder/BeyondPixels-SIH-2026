# Local setup (Windows PowerShell)

This source capture has been inspected, but this exact checkout was not run against the team's Windows model installation. Commands below are a reproducible starting point, with missing model and platform artifacts called out explicitly.

## Prerequisites

- Python 3.13, Flutter SDK and Windows Desktop build tools for a Windows UI build.
- Tesseract OCR installed and on `PATH` (or configured locally for pytesseract).
- Optional research models and their compatible dependencies, only from verified/licensed sources. See [MODEL_DATA.md](MODEL_DATA.md).

## Backend

From the repository root:

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:BEYONDPIXELS_DEMO_TOKEN = python -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy the current token to your local clipboard for the UI; do not paste it into a commit.
Set-Clipboard -Value $env:BEYONDPIXELS_DEMO_TOKEN
python app.py
```

In a second PowerShell window, verify `Invoke-RestMethod http://127.0.0.1:8001/health` and `Invoke-RestMethod http://127.0.0.1:8001/v1/capabilities`. The capabilities response reports optional models that are currently available. Clear the clipboard after entering the token in the UI: `Set-Clipboard -Value ''`.

If OCR is unavailable, confirm Tesseract installation. If media analysis reports model unavailable, obtain and verify the required model through the team's approved internal channel; no trained weights ship in this repository. The 21 September `requirements.txt` may not cover separate ONNX, C2PA and deepfake worker environments.

## Flutter

From a new terminal at the repository root:

```powershell
cd frontend
flutter pub get
flutter create --platforms=windows,android,web .
flutter run -d windows
```

`flutter create` generates the missing platform scaffold; review its diff before committing generated platform files. On the analysis screen set the backend URL to `http://127.0.0.1:8001` and paste the same demo token. Windows localhost refers to the same computer. For an Android emulator or another device, the endpoint and network configuration differ; this snapshot's cross-device path is unverified. Do not expose this local token API to a public network.

## Tests

```powershell
cd backend
python -m pytest tests -q
cd ..\frontend
flutter test
```

Some tests require fixtures or optional models absent from this capture; record skips/failures accurately and run the actual UI demo before claiming end-to-end success.

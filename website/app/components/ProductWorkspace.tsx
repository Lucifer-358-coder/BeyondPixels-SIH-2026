"use client";

import { useMemo, useState } from "react";

type CheckItem = {
  name: string;
  detail: string;
};

type ProductWorkspaceProps = {
  workflowLabel: string;
  title: string;
  description: string;
  acceptedFormats: string;
  inputHint: string;
  checks: CheckItem[];
  evidence: string[];
  accent: "document" | "media";
};

type BackendState = "unknown" | "checking" | "online" | "offline";
type RunState = "idle" | "running" | "success" | "error";

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function prettyValue(value: unknown) {
  if (value === null) return "null";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value, null, 2);
}

export default function ProductWorkspace({
  workflowLabel,
  title,
  description,
  acceptedFormats,
  inputHint,
  checks,
  evidence,
  accent,
}: ProductWorkspaceProps) {
  const [file, setFile] = useState<File | null>(null);
  const [sessionKey, setSessionKey] = useState("");
  const [expertOpen, setExpertOpen] = useState(false);
  const [backendState, setBackendState] = useState<BackendState>("unknown");
  const [runState, setRunState] = useState<RunState>("idle");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  const workflowPath = accent === "document" ? "document" : "media";

  const fileSummary = useMemo(() => {
    if (!file) return null;
    return {
      name: file.name,
      size: formatBytes(file.size),
      type: file.type || "Unknown browser MIME type",
    };
  }, [file]);

  async function checkBackend() {
    setBackendState("checking");
    try {
      const response = await fetch("/backend/health", { cache: "no-store" });
      setBackendState(response.ok ? "online" : "offline");
    } catch {
      setBackendState("offline");
    }
  }

  async function analyze() {
    if (!file || !sessionKey.trim()) return;

    setRunState("running");
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("image", file);

    try {
      const response = await fetch(`/backend/${workflowPath}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${sessionKey.trim()}`,
        },
        body: formData,
      });

      const payload = await response.json().catch(() => ({
        error: "Backend returned a response that was not valid JSON.",
      }));

      if (!response.ok) {
        const message =
          typeof payload?.error === "string"
            ? payload.error
            : `Backend request failed with HTTP ${response.status}.`;
        throw new Error(message);
      }

      setResult(payload as Record<string, unknown>);
      setRunState("success");
      setBackendState("online");
    } catch (cause) {
      setRunState("error");
      setError(cause instanceof Error ? cause.message : "Analysis request failed.");
    }
  }

  const canAnalyze = Boolean(file && sessionKey.trim() && runState !== "running");

  return (
    <main className={`workspace-page ${accent === "media" ? "workspace-media" : ""}`}>
      <nav className="nav shell workspace-nav">
        <a className="brand" href="/" aria-label="BeyondPixels home">
          <span className="brand-mark" aria-hidden="true">BP</span>
          <span>BeyondPixels</span>
        </a>
        <div className="workspace-switcher" aria-label="Workflow navigation">
          <a className={accent === "document" ? "active" : ""} href="/document-verification">
            Document Verification
          </a>
          <a className={accent === "media" ? "active" : ""} href="/ai-image-deepfake">
            AI Image & Deepfake
          </a>
        </div>
        <a className="nav-cta" href="/">Overview</a>
      </nav>

      <section className="workspace-hero shell">
        <div>
          <p className="kicker">{workflowLabel}</p>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        <div className="build-badge">
          <span className="pulse-dot" />
          DAY 2 · LIVE API WIRING
        </div>
      </section>

      <section className="workspace-grid shell">
        <div className="workspace-main">
          <article className="product-panel upload-panel">
            <div className="panel-heading">
              <div>
                <span className="panel-index">01</span>
                <h2>Provide evidence</h2>
              </div>
              <span className="panel-state">MULTIPART / IMAGE</span>
            </div>

            <label className={`dropzone ${file ? "has-file" : ""}`}>
              <input
                type="file"
                accept={acceptedFormats}
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                  setResult(null);
                  setError("");
                  setRunState("idle");
                }}
              />
              <span className="drop-icon" aria-hidden="true">↑</span>
              <strong>{file ? "Replace selected file" : "Select a file for this workflow"}</strong>
              <span>{inputHint}</span>
              <small>
                The selected image is sent only when you press Analyze. Use synthetic, fictional or authorized material.
              </small>
            </label>

            {fileSummary && (
              <div className="selected-file" aria-live="polite">
                <div className="file-mark">FILE</div>
                <div>
                  <strong>{fileSummary.name}</strong>
                  <span>{fileSummary.size} · {fileSummary.type}</span>
                </div>
                <button type="button" onClick={() => setFile(null)}>Remove</button>
              </div>
            )}
          </article>

          <article className="product-panel checks-panel">
            <div className="panel-heading">
              <div>
                <span className="panel-index">02</span>
                <h2>Analysis plan</h2>
              </div>
              <span className="panel-state">BACKEND CAPABILITY MAP</span>
            </div>

            <div className="module-list">
              {checks.map((check) => (
                <div className="module-row" key={check.name}>
                  <span className="module-indicator" />
                  <div>
                    <strong>{check.name}</strong>
                    <p>{check.detail}</p>
                  </div>
                  <span className="module-status">Backend driven</span>
                </div>
              ))}
            </div>
          </article>

          {(result || error) && (
            <article className="product-panel result-panel" aria-live="polite">
              <div className="panel-heading">
                <div>
                  <span className="panel-index">04</span>
                  <h2>{error ? "Analysis error" : "Backend result"}</h2>
                </div>
                <span className={`panel-state ${error ? "result-error" : "result-success"}`}>
                  {error ? "REQUEST FAILED" : "LIVE RESPONSE"}
                </span>
              </div>

              {error ? (
                <p className="result-message">{error}</p>
              ) : (
                <div className="result-grid">
                  {Object.entries(result ?? {}).map(([key, value]) => (
                    <div className="result-item" key={key}>
                      <span>{key.replaceAll("_", " ")}</span>
                      <pre>{prettyValue(value)}</pre>
                    </div>
                  ))}
                </div>
              )}
            </article>
          )}
        </div>

        <aside className="workspace-side">
          <article className="product-panel action-panel">
            <span className="panel-index">03</span>
            <h2>Analysis readiness</h2>

            <label className="session-field">
              <span>Local demo session key</span>
              <input
                type="password"
                value={sessionKey}
                onChange={(event) => setSessionKey(event.target.value)}
                placeholder="Paste the current backend demo key"
                autoComplete="off"
              />
              <small>Kept only in this page state; it is not saved to the repository.</small>
            </label>

            <div className="readiness-row">
              <span>Evidence selected</span>
              <strong className={file ? "ready" : ""}>{file ? "Ready" : "Required"}</strong>
            </div>
            <div className="readiness-row">
              <span>Session key</span>
              <strong className={sessionKey.trim() ? "ready" : ""}>
                {sessionKey.trim() ? "Provided" : "Required"}
              </strong>
            </div>
            <div className="readiness-row">
              <span>Backend connection</span>
              <strong className={backendState === "online" ? "ready" : ""}>
                {backendState === "unknown" && "Not checked"}
                {backendState === "checking" && "Checking"}
                {backendState === "online" && "Online"}
                {backendState === "offline" && "Offline"}
              </strong>
            </div>

            <button className="secondary-action" type="button" onClick={checkBackend} disabled={backendState === "checking"}>
              {backendState === "checking" ? "Checking backend..." : "Check backend"}
            </button>

            <button className="analyze-button live" type="button" disabled={!canAnalyze} onClick={analyze}>
              {runState === "running" ? "Analyzing..." : "Analyze with BeyondPixels"}
            </button>
            <p className="button-note">
              Sends multipart field <code>image</code> to the verified local Flask workflow route.
            </p>
          </article>

          <article className="product-panel evidence-panel">
            <span className="panel-index">RESULT DESIGN</span>
            <h2>Evidence the reviewer can receive</h2>
            <div className="evidence-tags">
              {evidence.map((item) => <span key={item}>{item}</span>)}
            </div>
            <p>
              The UI preserves inconclusive, unavailable and manual-review states rather than inventing a binary verdict.
            </p>
          </article>

          <article className="product-panel expert-panel">
            <button
              className="expert-toggle"
              type="button"
              onClick={() => setExpertOpen((value) => !value)}
              aria-expanded={expertOpen}
            >
              <span>
                <small>PROGRESSIVE DISCLOSURE</small>
                Expert / Judge view
              </span>
              <b>{expertOpen ? "−" : "+"}</b>
            </button>
            {expertOpen && (
              <div className="expert-content">
                <p>Current integration details:</p>
                <ul>
                  <li>Flask backend default: 127.0.0.1:8001</li>
                  <li>Document route: /v1/screen</li>
                  <li>Media route: /api/v1/detect/image</li>
                  <li>multipart field: image</li>
                  <li>authorization: temporary Bearer demo session key</li>
                </ul>
              </div>
            )}
          </article>
        </aside>
      </section>

      <footer className="workspace-footer shell">
        <span>BeyondPixels · Human reviewer remains the final decision-maker.</span>
        <a href="/">Return to platform overview</a>
      </footer>
    </main>
  );
}

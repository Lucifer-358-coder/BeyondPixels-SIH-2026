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

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
  const [expertOpen, setExpertOpen] = useState(false);

  const fileSummary = useMemo(() => {
    if (!file) return null;
    return {
      name: file.name,
      size: formatBytes(file.size),
      type: file.type || "Unknown browser MIME type",
    };
  }, [file]);

  return (
    <main className={`workspace-page ${accent === "media" ? "workspace-media" : ""}`}>
      <nav className="nav shell workspace-nav">
        <a className="brand" href="/" aria-label="BeyondPixels home">
          <span className="brand-mark" aria-hidden="true">BP</span>
          <span>BeyondPixels</span>
        </a>
        <div className="workspace-switcher" aria-label="Workflow navigation">
          <a
            className={accent === "document" ? "active" : ""}
            href="/document-verification"
          >
            Document Verification
          </a>
          <a
            className={accent === "media" ? "active" : ""}
            href="/ai-image-deepfake"
          >
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
          DAY 2 UI · BACKEND NOT CONNECTED
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
              <span className="panel-state">LOCAL SELECTION</span>
            </div>

            <label className={`dropzone ${file ? "has-file" : ""}`}>
              <input
                type="file"
                accept={acceptedFormats}
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              <span className="drop-icon" aria-hidden="true">↑</span>
              <strong>{file ? "Replace selected file" : "Select a file for this workflow"}</strong>
              <span>{inputHint}</span>
              <small>This Day 2 interface keeps the file in your browser. It is not uploaded to a server yet.</small>
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
              <span className="panel-state">CAPABILITY MAP</span>
            </div>

            <div className="module-list">
              {checks.map((check) => (
                <div className="module-row" key={check.name}>
                  <span className="module-indicator" />
                  <div>
                    <strong>{check.name}</strong>
                    <p>{check.detail}</p>
                  </div>
                  <span className="module-status">Awaiting API</span>
                </div>
              ))}
            </div>
          </article>
        </div>

        <aside className="workspace-side">
          <article className="product-panel action-panel">
            <span className="panel-index">03</span>
            <h2>Analysis readiness</h2>
            <div className="readiness-row">
              <span>Evidence selected</span>
              <strong className={file ? "ready" : ""}>{file ? "Ready" : "Required"}</strong>
            </div>
            <div className="readiness-row">
              <span>Backend connection</span>
              <strong>Pending</strong>
            </div>
            <button className="analyze-button" type="button" disabled>
              Analyze with BeyondPixels
            </button>
            <p className="button-note">
              Disabled intentionally until the real Flask endpoint is integrated and verified.
            </p>
          </article>

          <article className="product-panel evidence-panel">
            <span className="panel-index">RESULT DESIGN</span>
            <h2>Evidence the reviewer will see</h2>
            <div className="evidence-tags">
              {evidence.map((item) => <span key={item}>{item}</span>)}
            </div>
            <p>
              Results will use supported, suspicious, inconclusive, unavailable, or manual-review states instead of forcing unsupported conclusions.
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
                <p>Planned technical detail layer:</p>
                <ul>
                  <li>module/model availability</li>
                  <li>model or rule version identifiers</li>
                  <li>processing time</li>
                  <li>raw per-module scores only when meaningful</li>
                  <li>technical reason for unavailable or inconclusive checks</li>
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

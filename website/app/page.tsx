const workflows = [
  {
    eyebrow: "01 / Identity integrity",
    title: "Document Verification",
    description:
      "Review OCR, MRZ, consistency, validity, tampering, provenance and supported face-verification evidence without exposing backend complexity.",
    checks: ["OCR & MRZ", "Tampering", "Face verification"],
  },
  {
    eyebrow: "02 / Media authenticity",
    title: "AI Image and Deepfake Detection",
    description:
      "Separate whole-image AI-generation analysis from face/deepfake manipulation signals and present only actionable evidence to the reviewer.",
    checks: ["AI-image analysis", "Deepfake analysis", "Explainable evidence"],
  },
];

const principles = [
  "Evidence before decoration",
  "Backend complexity stays hidden",
  "Unavailable checks remain visible",
  "Human reviewer stays in control",
];

export default function Home() {
  return (
    <main>
      <nav className="nav shell">
        <a className="brand" href="#top" aria-label="BeyondPixels home">
          <span className="brand-mark" aria-hidden="true">BP</span>
          <span>BeyondPixels</span>
        </a>
        <div className="nav-links" aria-label="Primary navigation">
          <a href="#platform">Platform</a>
          <a href="#approach">Approach</a>
          <a href="#progress">Progress</a>
        </div>
        <a className="nav-cta" href="#platform">Enter platform</a>
      </nav>

      <section className="hero shell" id="top">
        <div className="hero-copy">
          <p className="kicker"><span className="pulse-dot" /> AI-assisted screening intelligence</p>
          <h1>
            See the evidence.
            <span>Not the backend noise.</span>
          </h1>
          <p className="hero-text">
            BeyondPixels brings document intelligence and synthetic-media analysis
            into one focused review experience built for fast, explainable decisions.
          </p>
          <div className="hero-actions">
            <a className="button primary" href="#platform">Explore BeyondPixels</a>
            <a className="button ghost" href="#approach">How it works</a>
          </div>
          <div className="trust-row" aria-label="Product principles">
            {principles.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </div>

        <div className="analysis-core" aria-label="BeyondPixels analysis preview">
          <div className="core-grid" />
          <div className="core-orbit orbit-one" />
          <div className="core-orbit orbit-two" />
          <div className="core-center">
            <span className="core-label">BEYONDPIXELS</span>
            <strong>ANALYSIS CORE</strong>
            <span className="core-status">SYSTEM READY</span>
          </div>
          <div className="signal-card signal-a">
            <span>DOCUMENT SIGNALS</span>
            <strong>Evidence mapped</strong>
          </div>
          <div className="signal-card signal-b">
            <span>MEDIA SIGNALS</span>
            <strong>Separate analysis</strong>
          </div>
        </div>
      </section>

      <section className="platform shell section" id="platform">
        <div className="section-heading">
          <p className="kicker">Two workflows. One review language.</p>
          <h2>Choose the analysis path that matches the evidence.</h2>
          <p>
            Document authenticity and synthetic-media detection remain clearly separated
            so one model output is never mistaken for a complete verification decision.
          </p>
        </div>

        <div className="workflow-grid">
          {workflows.map((workflow) => (
            <article className="workflow-card" key={workflow.title}>
              <div className="card-topline">
                <span>{workflow.eyebrow}</span>
                <span className="status-dot">DESIGNED</span>
              </div>
              <h3>{workflow.title}</h3>
              <p>{workflow.description}</p>
              <div className="check-row">
                {workflow.checks.map((check) => <span key={check}>{check}</span>)}
              </div>
              <span className="card-link">Interactive workflow screen is next</span>
            </article>
          ))}
        </div>
      </section>

      <section className="approach shell section" id="approach">
        <div className="section-heading narrow">
          <p className="kicker">Operator-first UX</p>
          <h2>Complex analysis underneath. Simple decisions on top.</h2>
        </div>
        <div className="approach-grid">
          <article>
            <span className="step">01</span>
            <h3>Upload</h3>
            <p>Give the system only the evidence required by the selected workflow.</p>
          </article>
          <article>
            <span className="step">02</span>
            <h3>Analyze</h3>
            <p>Backend models, rules and forensic checks run without cluttering the interface.</p>
          </article>
          <article>
            <span className="step">03</span>
            <h3>Review</h3>
            <p>See status, supported confidence, extracted evidence and reasons for manual review.</p>
          </article>
        </div>
      </section>

      <section className="progress shell section" id="progress">
        <div className="progress-panel">
          <div>
            <p className="kicker">Build status / Day 1</p>
            <h2>Website foundation in progress.</h2>
          </div>
          <div className="progress-list">
            <span><b>✓</b> AI Cybersecurity SaaS direction frozen</span>
            <span><b>✓</b> Operator information hierarchy defined</span>
            <span><b>✓</b> Two core workflows separated</span>
            <span><b>•</b> Interactive product screens next</span>
          </div>
        </div>
      </section>
    </main>
  );
}

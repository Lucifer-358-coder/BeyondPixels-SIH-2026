import ProductWorkspace from "../components/ProductWorkspace";

const checks = [
  {
    name: "AI-generated image screening",
    detail: "Evaluate supported whole-image generation signals without presenting a detector score as standalone proof.",
  },
  {
    name: "Deepfake / face manipulation",
    detail: "Run the separate face-manipulation path when a detectable face and supported input are available.",
  },
  {
    name: "Visual forensic signals",
    detail: "Combine supported texture, compression, frequency or learned visual observations as evidence.",
  },
  {
    name: "Explainable observations",
    detail: "Translate module output into reviewer-readable reasons, including inconclusive and unavailable states.",
  },
];

const evidence = [
  "AI-image observations",
  "Deepfake observations",
  "Detected-face status",
  "Forensic signals",
  "Supported confidence",
  "Inconclusive reasons",
  "Unavailable checks",
  "Recommended review action",
];

export default function AiImageDeepfakePage() {
  return (
    <ProductWorkspace
      workflowLabel="02 / Media authenticity"
      title="AI Image and Deepfake Detection"
      description="Keep synthetic-image screening and face/deepfake analysis in a dedicated media-authenticity workflow so their evidence is never confused with complete document verification."
      acceptedFormats="image/png,image/jpeg,image/webp"
      inputHint="PNG, JPG or WEBP · higher-quality images improve the evidence available to supported modules"
      checks={checks}
      evidence={evidence}
      accent="media"
    />
  );
}

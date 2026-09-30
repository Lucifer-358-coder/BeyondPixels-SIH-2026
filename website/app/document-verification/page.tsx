import ProductWorkspace from "../components/ProductWorkspace";

const checks = [
  {
    name: "OCR & field extraction",
    detail: "Extract visible document text and structure for downstream consistency review.",
  },
  {
    name: "MRZ & consistency",
    detail: "Compare machine-readable information, printed fields, dates and supported checksums.",
  },
  {
    name: "Tampering indicators",
    detail: "Surface visual anomalies, copy-move signals and other supported forensic observations.",
  },
  {
    name: "Face verification",
    detail: "Use supported face-comparison evidence only when an appropriate portrait is available.",
  },
  {
    name: "Metadata & provenance",
    detail: "Report available provenance or metadata observations without treating absence as proof of fraud.",
  },
];

const evidence = [
  "Extracted fields",
  "MRZ observations",
  "Consistency issues",
  "Date / validity checks",
  "Tampering evidence",
  "Face comparison",
  "Metadata / provenance",
  "Recommended review action",
];

export default function DocumentVerificationPage() {
  return (
    <ProductWorkspace
      workflowLabel="01 / Identity integrity"
      title="Document Verification"
      description="Screen passports, visas and supported identity-document evidence through a focused reviewer workspace. Backend checks stay underneath; evidence and review actions stay visible."
      acceptedFormats="image/png,image/jpeg,image/webp,application/pdf"
      inputHint="PNG, JPG, WEBP or PDF · use synthetic, fictional or authorized samples"
      checks={checks}
      evidence={evidence}
      accent="document"
    />
  );
}

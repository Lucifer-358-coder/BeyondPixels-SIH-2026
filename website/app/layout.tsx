import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BeyondPixels | AI-Assisted Screening",
  description:
    "BeyondPixels combines Document Verification with AI Image and Deepfake Detection in an evidence-first review experience.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

import type { NextConfig } from "next";

const backend = (process.env.BEYONDPIXELS_BACKEND_URL || "http://127.0.0.1:8001").replace(/\/$/, "");

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: "/backend/health",
        destination: `${backend}/health`,
      },
      {
        source: "/backend/document",
        destination: `${backend}/v1/screen`,
      },
      {
        source: "/backend/media",
        destination: `${backend}/api/v1/detect/image`,
      },
    ];
  },
};

export default nextConfig;

import type { NextConfig } from "next";

const figmaDevOrigin =
  process.env.FIGMA && process.env.FIGMA_PUBLIC_URL
    ? new URL(process.env.FIGMA_PUBLIC_URL).hostname
    : undefined;

// The production image (infra/docker/Dockerfile.web) copies .next/standalone
// and runs `node server.js`, so the build must emit a self-contained server.
// The app is fully self-contained in apps/web: no workspace transpilePackages
// and no remote images are needed in this phase.
const nextConfig: NextConfig = {
  output: "standalone",
  ...(figmaDevOrigin ? { allowedDevOrigins: [figmaDevOrigin] } : {}),
  // Do not generate per-directory agent instruction files on `next dev`.
  agentRules: false,
};

export default nextConfig;

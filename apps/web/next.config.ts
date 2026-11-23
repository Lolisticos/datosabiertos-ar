import type { NextConfig } from "next";

// The production image (infra/docker/Dockerfile.web) copies .next/standalone
// and runs `node server.js`, so the build must emit a self-contained server.
// The app is fully self-contained in apps/web: no workspace transpilePackages
// and no remote images are needed in this phase.
const nextConfig: NextConfig = {
  output: "standalone",
  // Do not generate per-directory agent instruction files on `next dev`.
  agentRules: false,
};

export default nextConfig;

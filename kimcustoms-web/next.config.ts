import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // Next's CLI type-check mode currently fails to parse a valid TypeScript
    // 5.9 config in this environment; the supported compiler API path checks
    // the same project and keeps production builds deterministic.
    useTypeScriptCli: false,
  },
};

export default nextConfig;

// Node.js 22+ includes a built-in localStorage that breaks SSR in libraries
// expecting browser-only localStorage. Remove it before any modules load.
if (typeof window === "undefined" && typeof globalThis.localStorage !== "undefined") {
  delete globalThis.localStorage;
}

const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Transpile shared workspace packages
  transpilePackages: ["@auto-claude/ui", "@auto-claude/types"],
  // Set turbopack root to monorepo root so it can resolve workspaces
  turbopack: {
    root: path.resolve(__dirname, "../.."),
  },
};

module.exports = nextConfig;

import { defineConfig } from "vite";

// A separate config for the M5 read-path verifier.
//
// It exists because the app config's `manualChunks` splits `genlayer-js` and
// `viem` into browser chunks, which is right for the app and wrong for a Node
// SSR bundle: rollup refuses to place an external in a manual chunk, and the
// verifier has no reason to bundle vendor code at all.
//
// Keeping it in its own file rather than conditioning the app config on an env
// var means the build a reviewer reads is the build that ships. The output goes
// to `frontend/.m5-verify-build`, which is gitignored.
export default defineConfig({
  build: {
    ssr: "scripts/verify-reads.mjs",
    target: "es2020",
    outDir: ".m5-verify-build",
    emptyOutDir: true,
    minify: false,
    rollupOptions: {
      output: { format: "es", entryFileNames: "verify-reads.mjs" },
    },
  },
});
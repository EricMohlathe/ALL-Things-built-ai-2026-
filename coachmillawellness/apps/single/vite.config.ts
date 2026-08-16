import { resolve } from 'node:path';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, type Plugin } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';

const root = resolve(import.meta.dirname, '../..');

/**
 * Ships the artefact under the name §6 specifies, and again as `index.html`.
 *
 * Two names, one file, for two ways of receiving it. She gets the artefact
 * directly — over WhatsApp, on a USB stick, in her Files app — where
 * `index.html` sitting in her downloads folder among a dozen others is the wrong
 * deliverable. A static host, meanwhile, serves `index.html` at the root URL and
 * nothing else, so without the copy the deployed site is a 404.
 *
 * They are byte-identical by construction, and gate G3 asserts it — the failure
 * this guards against is the two drifting into genuinely different pages, which
 * would quietly end the "one file" promise.
 */
function nameOutput(filename: string): Plugin {
  return {
    name: 'cmw:name-output',
    enforce: 'post',
    generateBundle(_options, bundle) {
      const entry = bundle['index.html'];
      if (!entry) return;
      bundle[filename] = { ...entry, fileName: filename };
    },
  };
}

/**
 * Build 1 — one HTML file, zero external requests (§6).
 *
 * `viteSingleFile` inlines every asset into the document. The workspace packages
 * are aliased straight to their TypeScript sources so there is no build step
 * between them and this app: one type-check, one bundle, and edits to a shared
 * component show up here immediately in dev.
 */
export default defineConfig({
  plugins: [react(), tailwindcss(), viteSingleFile(), nameOutput('CoachMillaWellness.html')],

  resolve: {
    /**
     * Array form, and the CSS subpaths come first — Vite matches aliases in
     * order by prefix, so a bare `@cmw/tokens` entry listed above them would
     * rewrite `@cmw/tokens/tokens.css` into `…/index.ts/tokens.css`.
     */
    alias: [
      {
        find: '@cmw/tokens/tokens.css',
        replacement: resolve(root, 'packages/tokens/src/tokens.css'),
      },
      {
        find: '@cmw/tokens/theme.css',
        replacement: resolve(root, 'packages/tokens/src/theme.css'),
      },
      { find: '@cmw/ui/styles.css', replacement: resolve(root, 'packages/ui/src/styles/styles.css') },
      { find: '@cmw/ai', replacement: resolve(root, 'packages/ai/src/index.ts') },
      { find: '@cmw/core', replacement: resolve(root, 'packages/core/src/index.ts') },
      { find: '@cmw/data', replacement: resolve(root, 'packages/data/src/index.ts') },
      { find: '@cmw/tokens', replacement: resolve(root, 'packages/tokens/src/index.ts') },
      { find: '@cmw/ui', replacement: resolve(root, 'packages/ui/src/index.ts') },
    ],
  },

  build: {
    target: 'es2022',
    // The file is opened from a filesystem, so a sourcemap alongside it would be
    // a second file that never travels with it.
    sourcemap: false,
    cssCodeSplit: false,
    assetsInlineLimit: 100_000_000,
    chunkSizeWarningLimit: 2000,
    rollupOptions: {
      output: {
        // One chunk: code-splitting is meaningless when everything is inlined
        // into a single document, and manual chunks would defeat the plugin.
        manualChunks: undefined,
        inlineDynamicImports: true,
      },
    },
  },

  server: { port: 5173 },
});

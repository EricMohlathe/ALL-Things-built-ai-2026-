/**
 * Build 1 entry point.
 *
 * Deliberately thin: pick a store, mount the shared app. Every screen, rule and
 * pixel comes from the workspace packages, so the web and desktop entries in P5
 * and P8 are the same six lines with a different adapter.
 */

import { CmwApp, useStore } from '@cmw/ui';
import { openBestStore } from '@cmw/data';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import './styles.css';

const container = document.getElementById('root');
if (!container) throw new Error('Missing #root — the shell HTML did not load.');

/**
 * A small, deliberate automation surface.
 *
 * The G2 round-trip gate drives export and restore through this rather than
 * through browser download plumbing, so the test asserts on *her data* instead of
 * on Chromium's file handling. It is also genuinely hers to use: this file is a
 * local document she owns, and scripting her own backup from the console is a
 * reasonable thing for an offline-first tool to allow.
 *
 * Nothing secret passes through it — it exposes only what the Vault screen
 * already does with a button.
 */
Object.defineProperty(window, '__cmw', {
  value: {
    exportBackup: () => useStore.getState().exportBackup(),
    importBackup: (json: string) => useStore.getState().importBackup(json),
    loadSample: () => useStore.getState().loadSample(),
    clearAll: () => useStore.getState().clearAll(),
  },
  writable: false,
  configurable: false,
});

createRoot(container).render(
  <StrictMode>
    {/* IndexedDB when the browser allows it, memory when it does not, so the app
        still opens in private browsing rather than failing at boot. */}
    <CmwApp store={openBestStore} />
  </StrictMode>,
);

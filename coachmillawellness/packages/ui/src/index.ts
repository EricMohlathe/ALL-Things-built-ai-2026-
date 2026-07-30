/**
 * @cmw/ui — the shared React UI.
 *
 * Web, the single HTML file and the Tauri desktop shell all mount `CmwApp` from
 * here. Mobile (P7) re-skins the same modules in React Native primitives while
 * reusing core, data and tokens unchanged.
 */

export { CmwApp, type CmwAppProps } from './app/CmwApp.js';
export { Shell, ThemeToggle, Wordmark } from './app/Shell.js';
export {
  hrefFor,
  navKeyFor,
  navigate,
  parseHash,
  useRoute,
  type ClientTab,
  type NavKey,
  type Route,
} from './app/router.js';
export {
  actionsFor,
  allSessions,
  coacheeById,
  goalsFor,
  liveActions,
  liveCoachees,
  liveContent,
  livePillars,
  scoresFor,
  sessionsFor,
  useStore,
  wheelRowsFor,
  type Status,
  type Toast,
} from './app/store.js';

export * from './primitives/index.js';
export * from './charts/index.js';

export { LivingWheel, type LivingWheelProps, type WheelDomainValue } from './wheel/LivingWheel.js';
export * from './wheel/geometry.js';
export {
  downloadBlob,
  downloadText,
  wheelPngBlob,
  wheelSvgMarkup,
  type WheelExportOptions,
} from './wheel/export.js';

export { Deck } from './modules/Deck.js';
export { Clients } from './modules/Clients.js';
export { ClientDetail } from './modules/ClientDetail.js';
export { Sessions } from './modules/Sessions.js';
export { SessionDetail } from './modules/SessionDetail.js';
export { WheelLab } from './modules/WheelLab.js';
export { Content } from './modules/Content.js';
export { Vault } from './modules/Vault.js';

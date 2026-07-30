/**
 * The application root.
 *
 * Every target mounts this: the single HTML file, the hosted web app, and the
 * Tauri desktop shell. The only thing that differs between them is the
 * `DataStore` handed in, which is what makes "Web + HTML + Desktop share the
 * exact same React UI" (§5.1) literally true rather than aspirational.
 */

import type { DescribableStore } from '@cmw/data';
import { useEffect } from 'react';

import { Deck } from '../modules/Deck.js';
import { ClientDetail } from '../modules/ClientDetail.js';
import { Clients } from '../modules/Clients.js';
import { Content } from '../modules/Content.js';
import { SessionDetail } from '../modules/SessionDetail.js';
import { Sessions } from '../modules/Sessions.js';
import { Vault } from '../modules/Vault.js';
import { WheelLab } from '../modules/WheelLab.js';
import { Button, Card, Skeleton, Toaster } from '../primitives/index.js';
import { Shell, ThemeToggle } from './Shell.js';
import { navigate, useRoute } from './router.js';
import { useStore } from './store.js';

export interface CmwAppProps {
  /** Resolves to the store this target uses. Called once on mount. */
  store: () => Promise<DescribableStore>;
}

export function CmwApp({ store }: CmwAppProps) {
  const route = useRoute();
  const status = useStore((state) => state.status);
  const error = useStore((state) => state.error);
  const data = useStore((state) => state.data);
  const theme = useStore((state) => state.theme);
  const storeKind = useStore((state) => state.storeKind);
  const toasts = useStore((state) => state.toasts);

  useEffect(() => {
    void store().then((resolved) => useStore.getState().init(resolved));
  }, [store]);

  // The theme is an attribute on the root element; every token switches with it.
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const themeToggle = (
    <ThemeToggle theme={theme} onChange={(next) => useStore.getState().setTheme(next)} />
  );

  return (
    <Shell route={route} themeToggle={themeToggle}>
      {status === 'loading' ? (
        <LoadingState />
      ) : status === 'error' ? (
        <Card className="border-danger/40">
          <h1 className="font-display text-xl text-hi">Could not open your data</h1>
          <p className="mt-2 text-sm text-lo">{error}</p>
          <p className="mt-2 text-sm text-lo">
            This usually means the browser is blocking storage. The app still works — it just will
            not remember anything after you close the tab.
          </p>
          <Button variant="quiet" className="mt-4" onClick={() => window.location.reload()}>
            Try again
          </Button>
        </Card>
      ) : (
        <Routed route={route} data={data} storeKind={storeKind} theme={theme} />
      )}

      <Toaster toasts={toasts} onDismiss={(id) => useStore.getState().dismissToast(id)} />
    </Shell>
  );
}

function Routed({
  route,
  data,
  storeKind,
  theme,
}: {
  route: ReturnType<typeof useRoute>;
  data: ReturnType<typeof useStore.getState>['data'];
  storeKind: ReturnType<typeof useStore.getState>['storeKind'];
  theme: ReturnType<typeof useStore.getState>['theme'];
}) {
  switch (route.name) {
    case 'deck':
      return <Deck data={data} onStart={() => void useStore.getState().loadSample()} />;
    case 'clients':
      return <Clients data={data} onAdd={(input) => useStore.getState().addCoachee(input)} />;
    case 'client':
      return <ClientDetail data={data} id={route.id} tab={route.tab} />;
    case 'sessions':
      return <Sessions data={data} openNew={false} />;
    case 'session-new':
      return <Sessions data={data} openNew />;
    case 'session':
      return <SessionDetail data={data} id={route.id} />;
    case 'wheel':
      return <WheelLab data={data} {...(route.id ? { id: route.id } : {})} />;
    case 'content':
      return <Content data={data} />;
    case 'vault':
      return <Vault data={data} storeKind={storeKind} theme={theme} />;
  }
}

/**
 * Skeletons shaped like the Deck, so the first paint does not jump. §4.4 asks for
 * a crossfade into content rather than a snap; the skeleton is what makes that
 * possible in the ~50ms it takes to read IndexedDB.
 */
function LoadingState() {
  return (
    <div>
      <Skeleton className="mb-7 h-40 w-full" />
      <div className="mb-7 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
    </div>
  );
}

export { navigate };

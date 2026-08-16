/**
 * Hash router (§6 — "one file, internal JS router").
 *
 * Hash-based rather than history-based because Build 1 is opened from a phone's
 * Files app over `file://`, where there is no server to answer a path and the
 * History API cannot help. The same router works unchanged when the app is served
 * from a domain, so nothing has to be swapped out for the web build.
 */

import { useEffect, useState } from 'react';

export type Route =
  | { name: 'deck' }
  | { name: 'clients' }
  | { name: 'client'; id: string; tab: ClientTab }
  | { name: 'sessions' }
  | { name: 'session'; id: string }
  | { name: 'session-new' }
  | { name: 'wheel'; id?: string }
  | { name: 'content' }
  | { name: 'insights' }
  | { name: 'vault' };

export type ClientTab = 'overview' | 'wheel' | 'sessions' | 'actions' | 'notes';

const CLIENT_TABS: ClientTab[] = ['overview', 'wheel', 'sessions', 'actions', 'notes'];

export function parseHash(hash: string): Route {
  const path = hash.replace(/^#\/?/, '').split('?')[0] ?? '';
  const parts = path.split('/').filter(Boolean);
  const [head, second, third] = parts;

  switch (head) {
    case undefined:
    case '':
    case 'deck':
      return { name: 'deck' };
    case 'clients':
      if (second === undefined) return { name: 'clients' };
      return {
        name: 'client',
        id: second,
        tab: CLIENT_TABS.includes(third as ClientTab) ? (third as ClientTab) : 'overview',
      };
    case 'sessions':
      if (second === undefined) return { name: 'sessions' };
      if (second === 'new') return { name: 'session-new' };
      return { name: 'session', id: second };
    case 'wheel':
      return second === undefined ? { name: 'wheel' } : { name: 'wheel', id: second };
    case 'content':
      return { name: 'content' };
    case 'insights':
      return { name: 'insights' };
    case 'vault':
      return { name: 'vault' };
    default:
      // An unknown route lands on the Deck rather than a dead end.
      return { name: 'deck' };
  }
}

export function hrefFor(route: Route): string {
  switch (route.name) {
    case 'deck':
      return '#/deck';
    case 'clients':
      return '#/clients';
    case 'client':
      return `#/clients/${route.id}/${route.tab}`;
    case 'sessions':
      return '#/sessions';
    case 'session':
      return `#/sessions/${route.id}`;
    case 'session-new':
      return '#/sessions/new';
    case 'wheel':
      return route.id ? `#/wheel/${route.id}` : '#/wheel';
    case 'content':
      return '#/content';
    case 'insights':
      return '#/insights';
    case 'vault':
      return '#/vault';
  }
}

export function navigate(route: Route): void {
  window.location.hash = hrefFor(route);
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() =>
    parseHash(typeof window === 'undefined' ? '' : window.location.hash),
  );

  useEffect(() => {
    const onChange = (): void => setRoute(parseHash(window.location.hash));
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);

  useEffect(() => {
    // A route change is a new page as far as the reader is concerned, so it
    // starts at the top — otherwise a deep scroll carries over into a short
    // screen and looks blank.
    window.scrollTo({ top: 0 });
  }, [route]);

  return route;
}

/** Which nav item should read as current for a given route. */
export type NavKey = 'deck' | 'clients' | 'sessions' | 'content' | 'more';

export function navKeyFor(route: Route): NavKey {
  switch (route.name) {
    case 'deck':
      return 'deck';
    case 'clients':
    case 'client':
      return 'clients';
    case 'sessions':
    case 'session':
    case 'session-new':
      return 'sessions';
    case 'content':
      return 'content';
    case 'wheel':
    case 'insights':
    case 'vault':
      return 'more';
  }
}

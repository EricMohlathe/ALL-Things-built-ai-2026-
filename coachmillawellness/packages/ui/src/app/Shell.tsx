/**
 * Navigation shell (§2).
 *
 * Left rail on desktop, bottom tab bar of five on mobile — the same five
 * destinations either way, so muscle memory transfers between her laptop and her
 * phone. "More" holds Wheel Lab and the Vault rather than a sixth tab, because a
 * six-item tab bar on a phone is four items and two mistakes.
 */

import {
  CircleGauge,
  FileText,
  LayoutGrid,
  MoreHorizontal,
  TrendingUp,
  Users,
  Video,
} from 'lucide-react';
import type { ReactNode } from 'react';
import { useState } from 'react';

import { IconButton, Modal, cn } from '../primitives/index.js';
import { hrefFor, navKeyFor, type NavKey, type Route } from './router.js';

interface NavItem {
  key: NavKey;
  label: string;
  icon: ReactNode;
  route: Route;
}

const ITEMS: NavItem[] = [
  { key: 'deck', label: 'Deck', icon: <LayoutGrid size={20} />, route: { name: 'deck' } },
  { key: 'clients', label: 'Clients', icon: <Users size={20} />, route: { name: 'clients' } },
  { key: 'sessions', label: 'Sessions', icon: <FileText size={20} />, route: { name: 'sessions' } },
  { key: 'content', label: 'Content', icon: <Video size={20} />, route: { name: 'content' } },
];

export function Shell({
  route,
  children,
  themeToggle,
}: {
  route: Route;
  children: ReactNode;
  themeToggle: ReactNode;
}) {
  const active = navKeyFor(route);
  const [moreOpen, setMoreOpen] = useState(false);

  const more = (
    <>
      <a
        href={hrefFor({ name: 'wheel' })}
        onClick={() => setMoreOpen(false)}
        className="flex min-h-11 items-center gap-3 rounded-md px-3 text-hi transition-colors duration-150 hover:bg-raised"
      >
        <CircleGauge size={18} />
        Wheel Lab
      </a>
      <a
        href={hrefFor({ name: 'insights' })}
        onClick={() => setMoreOpen(false)}
        className="flex min-h-11 items-center gap-3 rounded-md px-3 text-hi transition-colors duration-150 hover:bg-raised"
      >
        <TrendingUp size={18} />
        Insights
      </a>
      <a
        href={hrefFor({ name: 'vault' })}
        onClick={() => setMoreOpen(false)}
        className="flex min-h-11 items-center gap-3 rounded-md px-3 text-hi transition-colors duration-150 hover:bg-raised"
      >
        <MoreHorizontal size={18} />
        Vault &amp; settings
      </a>
    </>
  );

  return (
    <div className="min-h-screen bg-ink">
      {/* Keyboard users reach the content without walking the whole rail. */}
      <a
        href="#cmw-main"
        className="cmw-sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-70 focus:rounded-md focus:bg-surface focus:px-4 focus:py-2 focus:text-hi"
      >
        Skip to content
      </a>

      {/* ── Desktop rail ─────────────────────────────────────────────────── */}
      <nav
        aria-label="Main"
        className="cmw-glass fixed inset-y-0 left-0 z-40 hidden w-[13.5rem] flex-col border-y-0 border-l-0 p-4 lg:flex"
      >
        <Wordmark />
        <ul className="mt-6 flex flex-1 flex-col gap-1">
          {ITEMS.map((item) => (
            <li key={item.key}>
              <RailLink item={item} current={active === item.key} />
            </li>
          ))}
          <li className="mt-2 border-t border-edge pt-2">
            <div className="flex flex-col gap-1">{more}</div>
          </li>
        </ul>
        <div className="mt-4 border-t border-edge pt-3">{themeToggle}</div>
      </nav>

      {/* ── Mobile top bar ───────────────────────────────────────────────── */}
      <header className="cmw-glass-bar sticky top-0 z-30 flex items-center justify-between border-x-0 border-t-0 px-4 py-2.5 lg:hidden">
        <Wordmark compact />
        {themeToggle}
      </header>

      <main id="cmw-main" className="px-4 pb-28 pt-5 lg:ml-[13.5rem] lg:px-8 lg:pb-12">
        <div className="mx-auto w-full max-w-6xl">{children}</div>
      </main>

      {/* ── Mobile tab bar ───────────────────────────────────────────────── */}
      <nav
        aria-label="Main"
        className="cmw-glass-bar fixed inset-x-0 bottom-0 z-40 flex border-x-0 border-b-0 lg:hidden"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        {ITEMS.map((item) => (
          <TabLink key={item.key} item={item} current={active === item.key} />
        ))}
        <button
          type="button"
          onClick={() => setMoreOpen(true)}
          aria-current={active === 'more' ? 'page' : undefined}
          className={cn(
            'flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-xs',
            active === 'more' ? 'text-accent-ink' : 'text-lo',
          )}
        >
          <MoreHorizontal size={20} />
          More
        </button>
      </nav>

      <Modal open={moreOpen} onClose={() => setMoreOpen(false)} title="More">
        <div className="flex flex-col gap-1">{more}</div>
      </Modal>
    </div>
  );
}

function RailLink({ item, current }: { item: NavItem; current: boolean }) {
  return (
    <a
      href={hrefFor(item.route)}
      aria-current={current ? 'page' : undefined}
      className={cn(
        'flex min-h-11 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors duration-150',
        current ? 'bg-accent-quiet text-accent-ink' : 'text-lo hover:bg-raised hover:text-hi',
      )}
    >
      {item.icon}
      {item.label}
    </a>
  );
}

function TabLink({ item, current }: { item: NavItem; current: boolean }) {
  return (
    <a
      href={hrefFor(item.route)}
      aria-current={current ? 'page' : undefined}
      className={cn(
        'flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-xs',
        current ? 'text-accent-ink' : 'text-lo',
      )}
    >
      {item.icon}
      {item.label}
    </a>
  );
}

/**
 * The wordmark: "Coach Milla" in the display face, "WELLNESS" in tracked caps,
 * with the dawn gradient on the M (§ brand line).
 */
export function Wordmark({ compact = false }: { compact?: boolean }) {
  return (
    <a
      href={hrefFor({ name: 'deck' })}
      // It is a real navigation target, so it owes the same 44px as any other.
      className="inline-flex min-h-11 flex-col justify-center leading-none"
    >
      <span className={cn('font-display text-hi', compact ? 'text-lg' : 'text-xl')}>
        Coach{' '}
        <span
          className="bg-clip-text text-transparent"
          style={{ backgroundImage: 'var(--cmw-gradient-dawn)' }}
        >
          M
        </span>
        illa
      </span>
      <span
        className={cn(
          'font-medium text-lo',
          compact ? 'text-[0.6rem] tracking-[0.2em]' : 'text-[0.65rem] tracking-[0.24em]',
        )}
      >
        WELLNESS
      </span>
    </a>
  );
}

export function ThemeToggle({
  theme,
  onChange,
}: {
  theme: 'dawn' | 'morning';
  onChange: (theme: 'dawn' | 'morning') => void;
}) {
  const next = theme === 'dawn' ? 'morning' : 'dawn';
  return (
    <IconButton
      label={`Switch to ${next === 'dawn' ? 'Dawn' : 'Morning'} theme`}
      onClick={() => onChange(next)}
    >
      {theme === 'dawn' ? <SunIcon /> : <MoonIcon />}
    </IconButton>
  );
}

function SunIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </svg>
  );
}

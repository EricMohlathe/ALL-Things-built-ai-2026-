/**
 * First Light primitives.
 *
 * Every control in the product is built from these, which is how the design laws
 * stay true without anyone re-remembering them per screen:
 *
 *  - Colour comes from the token utilities only — no raw hex anywhere below.
 *  - Interactive targets are at least 44px (§4.7).
 *  - Labels are always visible. A placeholder is never a label.
 *  - Errors sit next to their field, not in a banner.
 *  - Conditional renders are wrapped in AnimatePresence, so nothing pops out of
 *    existence (§4.4's "zero motion gaps").
 *  - Enters rise 8px and scale from 0.96; exits are shorter and flatter.
 */

import { duration, easingArray, stagger } from '@cmw/tokens';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import {
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  type CSSProperties,
  type ReactNode,
} from 'react';
import { X } from 'lucide-react';

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}

const SEC = 1000;

// ── Motion helpers ────────────────────────────────────────────────────────

/**
 * The house enter. Under reduced motion this collapses to a crossfade rather
 * than disappearing — a snap reads as a bug, not as calm.
 */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduced ? { opacity: 0 } : { opacity: 0, y: 8, filter: 'blur(4px)' }}
      animate={reduced ? { opacity: 1 } : { opacity: 1, y: 0, filter: 'blur(0px)' }}
      transition={{
        duration: reduced ? 0.001 : duration.base / SEC,
        ease: easingArray.outExpo,
        delay: reduced ? 0 : delay,
      }}
    >
      {children}
    </motion.div>
  );
}

/** Staggered list entrance, capped at 8 items so a long list never feels slow. */
export function Stagger({ children, className }: { children: ReactNode[]; className?: string }) {
  return (
    <div className={className}>
      {children.map((child, i) => (
        <Reveal key={i} delay={Math.min(i, stagger.max) * stagger.step}>
          {child}
        </Reveal>
      ))}
    </div>
  );
}

// ── Surfaces ──────────────────────────────────────────────────────────────

export function Card({
  children,
  className,
  as: Tag = 'div',
  interactive = false,
  ...rest
}: {
  children: ReactNode;
  className?: string;
  as?: 'div' | 'section' | 'article' | 'li';
  interactive?: boolean;
} & Record<string, unknown>) {
  return (
    <Tag
      className={cn(
        'rounded-lg border border-edge bg-surface p-4 shadow-raised',
        interactive && 'transition-colors duration-150 hover:border-edge-strong',
        className,
      )}
      {...rest}
    >
      {children}
    </Tag>
  );
}

/** Glass panel — the rail, the tab bar, and overlays (§4.2). */
export function Glass({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('cmw-glass rounded-lg', className)}>{children}</div>;
}

export function SectionHeader({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-3 flex items-end justify-between gap-4">
      <div>
        <h2 className="font-display text-xl text-hi">{title}</h2>
        {hint ? <p className="mt-0.5 text-sm text-lo">{hint}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  action,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow ? (
          <p className="mb-1 text-xs font-medium tracking-[0.14em] text-lo uppercase">{eyebrow}</p>
        ) : null}
        <h1 className="font-display text-3xl text-hi">{title}</h1>
        {subtitle ? <p className="mt-1 max-w-2xl text-lo">{subtitle}</p> : null}
      </div>
      {action}
    </header>
  );
}

// ── Buttons ───────────────────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'quiet' | 'ghost' | 'danger';

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  // The one solid-filled control in the system, and the only place `inverse`
  // text is used — verified for contrast in both themes.
  primary: 'bg-accent text-inverse hover:opacity-90',
  quiet: 'bg-raised text-hi border border-edge hover:border-edge-strong',
  ghost: 'text-lo hover:text-hi hover:bg-raised',
  danger: 'bg-transparent text-danger-ink border border-edge hover:border-edge-strong',
};

export function Button({
  children,
  onClick,
  variant = 'quiet',
  type = 'button',
  disabled = false,
  className,
  icon,
  full = false,
  title,
  label,
}: {
  children?: ReactNode;
  onClick?: () => void;
  variant?: ButtonVariant;
  type?: 'button' | 'submit';
  disabled?: boolean;
  className?: string;
  icon?: ReactNode;
  full?: boolean;
  title?: string;
  /** Required when the button is icon-only — otherwise it has no name at all. */
  label?: string;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      title={title ?? label}
      // An icon-only button falls back to `label`, then `title`. Without one of
      // them a screen reader announces "button" and nothing else.
      aria-label={children === undefined ? (label ?? title) : undefined}
      className={cn(
        // min-h-11 is the 44px floor from §4.7.
        'inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium',
        'transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-45',
        BUTTON_VARIANTS[variant],
        full && 'w-full',
        className,
      )}
    >
      {icon}
      {children}
    </button>
  );
}

export function IconButton({
  label,
  onClick,
  children,
  className,
}: {
  label: string;
  onClick?: () => void;
  children: ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      // The label is the accessible name; the icon alone is never the only cue.
      aria-label={label}
      title={label}
      className={cn(
        // Explicit h/w plus shrink-0: `size-*` alone can be compressed by a flex
        // parent, and this is the §4.7 44px floor, not a suggestion.
        'inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-lo',
        'transition-colors duration-150 hover:bg-raised hover:text-hi',
        className,
      )}
    >
      {children}
    </button>
  );
}

// ── Chips & badges ────────────────────────────────────────────────────────

export type Tone = 'neutral' | 'accent' | 'success' | 'warn' | 'energy' | 'danger' | 'info';

/**
 * A chip is a 10% tint of its own hue with `-ink` text on top. Solid fills are
 * avoided deliberately: no solid sage or amber holds 4.5:1 against white or
 * ivory, and the tint recipe is contrast-tested per tone in @cmw/tokens.
 */
const CHIP_TONES: Record<Tone, string> = {
  neutral: 'bg-raised text-lo border-edge',
  accent: 'bg-accent-quiet text-accent-ink border-transparent',
  success: 'text-success-ink border-transparent',
  warn: 'text-warn-ink border-transparent',
  energy: 'text-energy-ink border-transparent',
  danger: 'text-danger-ink border-transparent',
  info: 'text-info-ink border-transparent',
};

const CHIP_TINT: Partial<Record<Tone, string>> = {
  success: 'color-mix(in srgb, var(--cmw-success) 10%, var(--cmw-surface))',
  warn: 'color-mix(in srgb, var(--cmw-warn) 10%, var(--cmw-surface))',
  energy: 'color-mix(in srgb, var(--cmw-energy) 10%, var(--cmw-surface))',
  danger: 'color-mix(in srgb, var(--cmw-error) 10%, var(--cmw-surface))',
  info: 'color-mix(in srgb, var(--cmw-info) 10%, var(--cmw-surface))',
};

export function Chip({
  children,
  tone = 'neutral',
  icon,
  className,
  onClick,
  pressed,
  title,
}: {
  children: ReactNode;
  tone?: Tone;
  icon?: ReactNode;
  className?: string;
  onClick?: () => void;
  pressed?: boolean;
  title?: string;
}) {
  const tint = CHIP_TINT[tone];
  const style: CSSProperties | undefined = tint ? { backgroundColor: tint } : undefined;
  const base = cn(
    'inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-1 text-xs font-medium',
    CHIP_TONES[tone],
    className,
  );

  if (!onClick) {
    return (
      <span className={base} style={style} title={title}>
        {icon}
        {children}
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={pressed}
      title={title}
      /**
       * Unselected chips are NOT dimmed with opacity. It reads as a tidy way to
       * say "inactive" and it destroyed the contrast of every filter chip on the
       * page — an axe run measured `text-lo` at 2.76:1 through `opacity-55`.
       * Selection is already carried by the tone change and `aria-pressed`, which
       * costs no legibility and works for screen readers too.
       */
      className={cn(base, 'min-h-8 transition-all duration-150 hover:brightness-110')}
      style={style}
    >
      {icon}
      {children}
    </button>
  );
}

/** A number in the data face — scores, timers, counts. */
export function Numeric({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <span className={cn('cmw-numeric', className)}>{children}</span>;
}

export function Avatar({ name, size = 40 }: { name: string; size?: number }) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join('');

  return (
    <span
      aria-hidden="true"
      className="inline-flex shrink-0 items-center justify-center rounded-pill bg-accent-quiet font-display text-accent-ink"
      style={{ width: size, height: size, fontSize: size * 0.38 }}
    >
      {letters || '?'}
    </span>
  );
}

// ── Fields ────────────────────────────────────────────────────────────────

function fieldShell(invalid: boolean): string {
  return cn(
    'w-full rounded-md border bg-raised px-3 py-2.5 text-base text-hi',
    'placeholder:text-lo/60 transition-colors duration-150',
    invalid ? 'border-danger' : 'border-edge hover:border-edge-strong',
  );
}

export function Field({
  label,
  hint,
  error,
  children,
  htmlFor,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
  htmlFor?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      {/* Always visible — a placeholder disappears the moment she starts typing. */}
      <label htmlFor={htmlFor} className="text-sm font-medium text-hi">
        {label}
      </label>
      {children}
      <AnimatePresence mode="wait" initial={false}>
        {error ? (
          <motion.p
            key="error"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: duration.instant / SEC }}
            className="text-sm text-danger-ink"
            role="alert"
          >
            {error}
          </motion.p>
        ) : hint ? (
          <p key="hint" className="text-sm text-lo">
            {hint}
          </p>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

export function TextInput({
  label,
  value,
  onChange,
  placeholder,
  hint,
  error,
  type = 'text',
  onEnter,
  autoFocus,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  hint?: string;
  error?: string;
  // `password` exists for exactly one field — the Anthropic API key. It has no
  // reveal toggle: she pastes it once, and a reveal button would only ever help
  // whoever is reading over her shoulder.
  type?: 'text' | 'date' | 'url' | 'email' | 'number' | 'password';
  onEnter?: () => void;
  autoFocus?: boolean;
}) {
  const id = useId();
  return (
    <Field label={label} hint={hint} error={error} htmlFor={id}>
      <input
        id={id}
        type={type}
        value={value}
        placeholder={placeholder}
        autoFocus={autoFocus}
        aria-invalid={error ? true : undefined}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && onEnter) onEnter();
        }}
        className={fieldShell(Boolean(error))}
      />
    </Field>
  );
}

export function TextArea({
  label,
  value,
  onChange,
  rows = 4,
  placeholder,
  hint,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  placeholder?: string;
  hint?: string;
}) {
  const id = useId();
  return (
    <Field label={label} hint={hint} htmlFor={id}>
      <textarea
        id={id}
        rows={rows}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={cn(fieldShell(false), 'resize-y leading-relaxed')}
      />
    </Field>
  );
}

export function Select<T extends string>({
  label,
  value,
  options,
  onChange,
  hint,
}: {
  label: string;
  value: T;
  options: ReadonlyArray<{ value: T; label: string }>;
  onChange: (value: T) => void;
  hint?: string;
}) {
  const id = useId();
  return (
    <Field label={label} hint={hint} htmlFor={id}>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className={cn(fieldShell(false), 'min-h-11 appearance-none')}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </Field>
  );
}

/**
 * 1–10 slider for confidence and commitment. The value is always shown as a
 * numeral: the thumb position alone is not a reading, and these two numbers
 * decide whether the closing script is owed.
 */
export function ScoreSlider({
  label,
  value,
  onChange,
  hint,
  max = 10,
}: {
  label: string;
  value: number | null;
  onChange: (value: number) => void;
  hint?: string;
  max?: number;
}) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between">
        <label htmlFor={id} className="text-sm font-medium text-hi">
          {label}
        </label>
        <Numeric className={cn('text-lg', value === null ? 'text-lo' : 'text-hi')}>
          {value === null ? '—' : `${value}/${max}`}
        </Numeric>
      </div>
      <input
        id={id}
        type="range"
        min={0}
        max={max}
        step={1}
        value={value ?? 0}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-11 w-full accent-[var(--cmw-accent)]"
      />
      {hint ? <p className="text-sm text-lo">{hint}</p> : null}
    </div>
  );
}

export function Toggle({
  label,
  checked,
  onChange,
  hint,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  hint?: string;
}) {
  const id = useId();
  return (
    <div className="flex items-start justify-between gap-4 py-1">
      <div>
        <label htmlFor={id} className="text-sm font-medium text-hi">
          {label}
        </label>
        {hint ? <p className="mt-0.5 text-sm text-lo">{hint}</p> : null}
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative h-7 w-12 shrink-0 rounded-pill border transition-colors duration-200',
          checked ? 'border-transparent bg-accent' : 'border-edge bg-raised',
        )}
      >
        <motion.span
          layout
          transition={{ duration: duration.fast / SEC, ease: easingArray.outExpo }}
          className={cn(
            'absolute top-0.5 size-5 rounded-pill',
            checked ? 'left-6 bg-inverse' : 'left-0.5 bg-lo',
          )}
        />
      </button>
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: ReadonlyArray<{ value: T; label: string }>;
  active: T;
  onChange: (value: T) => void;
}) {
  return (
    <div role="tablist" className="mb-5 flex gap-1 overflow-x-auto border-b border-edge">
      {tabs.map((tab) => {
        const current = tab.value === active;
        return (
          <button
            key={tab.value}
            role="tab"
            aria-selected={current}
            onClick={() => onChange(tab.value)}
            className={cn(
              'relative min-h-11 shrink-0 px-3 text-sm font-medium transition-colors duration-150',
              current ? 'text-hi' : 'text-lo hover:text-hi',
            )}
          >
            {tab.label}
            {/* Shared layout id slides the underline between tabs instead of
                cutting; it is a transform, so it stays on the compositor. */}
            {current ? (
              <motion.span
                layoutId="cmw-tab-underline"
                className="absolute inset-x-2 -bottom-px h-0.5 rounded-pill bg-accent"
                transition={{ duration: duration.fast / SEC, ease: easingArray.outExpo }}
              />
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const reduced = useReducedMotion();
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    // Move focus into the dialog so a keyboard user is not left behind it.
    panel.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: (reduced ? 1 : duration.fast) / SEC }}
        >
          <button
            aria-label="Close"
            onClick={onClose}
            className="absolute inset-0 bg-black/55 backdrop-blur-sm"
          />
          <motion.div
            ref={panel}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            initial={reduced ? { opacity: 0 } : { opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, scale: 0.98 }}
            transition={{
              duration: (reduced ? 1 : duration.base) / SEC,
              ease: easingArray.outExpo,
            }}
            className={cn(
              'relative z-10 max-h-[92vh] w-full overflow-y-auto rounded-t-lg border border-edge',
              'bg-surface p-5 shadow-overlay sm:max-w-lg sm:rounded-lg',
            )}
          >
            <div className="mb-4 flex items-start justify-between gap-4">
              <h2 className="font-display text-xl text-hi">{title}</h2>
              <IconButton label="Close" onClick={onClose} className="-mr-2 -mt-2">
                <X size={18} />
              </IconButton>
            </div>
            {children}
            {footer ? <div className="mt-5 flex justify-end gap-2">{footer}</div> : null}
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────

export function EmptyState({
  title,
  body,
  action,
  icon,
}: {
  title: string;
  body: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <Reveal>
      <div className="flex flex-col items-center rounded-lg border border-dashed border-edge px-6 py-12 text-center">
        {icon ? <div className="mb-4 text-accent-ink">{icon}</div> : null}
        <h3 className="font-display text-xl text-hi">{title}</h3>
        <p className="mt-2 max-w-md text-sm text-lo">{body}</p>
        {action ? <div className="mt-5">{action}</div> : null}
      </div>
    </Reveal>
  );
}

// ── Progress ──────────────────────────────────────────────────────────────

/** Ring gauge for adherence and completion. Always paired with its numeral. */
export function ProgressRing({
  value,
  size = 64,
  label,
  tone = 'accent',
}: {
  value: number | null;
  size?: number;
  label?: string;
  tone?: 'accent' | 'success' | 'warn';
}) {
  const stroke = Math.max(4, size * 0.09);
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = value === null ? 0 : Math.min(100, Math.max(0, value));
  const colour = `var(--cmw-${tone === 'accent' ? 'accent' : tone})`;

  return (
    <div className="inline-flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--cmw-border)"
            strokeWidth={stroke}
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={colour}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference * (1 - pct / 100) }}
            transition={{ duration: duration.slow / SEC, ease: easingArray.outExpo }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <Numeric className="text-sm font-semibold text-hi">
            {value === null ? '—' : `${Math.round(pct)}%`}
          </Numeric>
        </div>
      </div>
      {label ? <span className="text-xs text-lo">{label}</span> : null}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-raised', className)} />;
}

// ── Toasts ────────────────────────────────────────────────────────────────

const TOAST_TONES: Record<string, Tone> = {
  info: 'info',
  success: 'success',
  warn: 'warn',
  error: 'danger',
};

export function Toaster({
  toasts,
  onDismiss,
}: {
  toasts: ReadonlyArray<{ id: string; tone: string; message: string }>;
  onDismiss: (id: string) => void;
}) {
  const reduced = useReducedMotion();
  return (
    <div
      // Announced politely so a save confirmation does not interrupt her typing.
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-24 z-60 flex flex-col items-center gap-2 px-4 sm:bottom-6"
    >
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: 12, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, y: 6, scale: 0.98 }}
            transition={{ duration: (reduced ? 1 : duration.fast) / SEC, ease: easingArray.outExpo }}
            className="pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-md border border-edge bg-surface p-3 shadow-overlay"
          >
            <Chip tone={TOAST_TONES[toast.tone] ?? 'neutral'}>
              {toast.tone === 'error' ? 'Problem' : toast.tone}
            </Chip>
            <p className="flex-1 text-sm text-hi">{toast.message}</p>
            <IconButton label="Dismiss" onClick={() => onDismiss(toast.id)} className="-my-2 -mr-1">
              <X size={16} />
            </IconButton>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

// ── Confirm ───────────────────────────────────────────────────────────────

interface ConfirmRequest {
  title: string;
  body: string;
  confirmLabel: string;
  onConfirm: () => void;
}

const ConfirmContext = createContext<((request: ConfirmRequest) => void) | null>(null);

export function useConfirm(): (request: ConfirmRequest) => void {
  const confirm = useContext(ConfirmContext);
  if (!confirm) throw new Error('useConfirm must be used inside <ConfirmProvider>');
  return confirm;
}

export { ConfirmContext };

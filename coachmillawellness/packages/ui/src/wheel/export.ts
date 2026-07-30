/**
 * Wheel PNG export (§2 M3).
 *
 * Builds a *standalone* SVG rather than serialising the live DOM node. A detached
 * SVG loses the document's CSS custom properties, so a naive
 * `new XMLSerializer().serializeToString(node)` rasterises with every colour
 * missing — the classic version of this bug. Theme values are resolved to
 * literals here and drawn from the same geometry helpers the component uses, so
 * the export matches what she is looking at.
 *
 * Rendered at 1080×1080 by default: square is the shape that survives a WhatsApp
 * forward intact, which is where these end up.
 */

import { wheelHues } from '@cmw/tokens';

import {
  WHEEL_CENTRE,
  WHEEL_GRID_STEPS,
  WHEEL_HUB_RADIUS,
  WHEEL_LABEL_RADIUS,
  WHEEL_RIM_RADIUS,
  WHEEL_VIEWBOX,
  arcPath,
  labelPlacement,
  petalPath,
  radiusForScore,
  spokes,
} from './geometry.js';
import type { WheelDomainValue } from './LivingWheel.js';

const VIEWBOX = WHEEL_VIEWBOX;
const CENTRE = WHEEL_CENTRE;
const HUB_RADIUS = WHEEL_HUB_RADIUS;
const RIM_RADIUS = WHEEL_RIM_RADIUS;
const GRID_STEPS = WHEEL_GRID_STEPS;

export interface WheelExportOptions {
  domains: WheelDomainValue[];
  /** Shown above the wheel. First name only on anything client-facing. */
  title?: string;
  subtitle?: string;
  /** Output edge length in pixels. */
  pixels?: number;
  showTargets?: boolean;
}

interface ResolvedTheme {
  bg: string;
  surface: string;
  border: string;
  textHi: string;
  textLo: string;
  accent: string;
}

/** Reads the live theme so the export follows Dawn or Morning as displayed. */
function resolveTheme(): ResolvedTheme {
  const fallback: ResolvedTheme = {
    bg: '#0E0F1A',
    surface: '#161827',
    border: 'rgba(255,255,255,0.10)',
    textHi: '#F4F2ED',
    textLo: '#9DA0B4',
    accent: '#9A7BFF',
  };
  if (typeof document === 'undefined') return fallback;

  const styles = getComputedStyle(document.documentElement);
  const read = (name: string, backup: string): string =>
    styles.getPropertyValue(name).trim() || backup;

  return {
    bg: read('--cmw-bg', fallback.bg),
    surface: read('--cmw-surface', fallback.surface),
    border: read('--cmw-border', fallback.border),
    textHi: read('--cmw-text-hi', fallback.textHi),
    textLo: read('--cmw-text-lo', fallback.textLo),
    accent: read('--cmw-accent', fallback.accent),
  };
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** The standalone, self-contained SVG. Also usable directly as a share asset. */
export function wheelSvgMarkup(options: WheelExportOptions): string {
  const { domains, title, subtitle, showTargets = true } = options;
  const theme = resolveTheme();
  const layout = spokes(domains.length);

  const average =
    domains.length === 0 ? null : domains.reduce((sum, d) => sum + d.score, 0) / domains.length;

  // Padded canvas so the wordmark and heading have room around the wheel.
  const width = VIEWBOX;
  const height = VIEWBOX + 92;
  const wheelOffset = 62;

  const parts: string[] = [];

  parts.push(`<rect width="${width}" height="${height}" fill="${theme.bg}"/>`);

  if (title) {
    parts.push(
      `<text x="${CENTRE}" y="36" text-anchor="middle" font-family="Georgia, serif" font-size="24" fill="${theme.textHi}">${escapeXml(title)}</text>`,
    );
  }
  if (subtitle) {
    parts.push(
      `<text x="${CENTRE}" y="54" text-anchor="middle" font-family="system-ui, sans-serif" font-size="12" fill="${theme.textLo}">${escapeXml(subtitle)}</text>`,
    );
  }

  parts.push(`<g transform="translate(0 ${wheelOffset})">`);

  for (const step of GRID_STEPS) {
    parts.push(
      `<circle cx="${CENTRE}" cy="${CENTRE}" r="${radiusForScore(step, HUB_RADIUS, RIM_RADIUS)}" fill="none" stroke="${theme.border}" stroke-width="${step === 10 ? 1.5 : 1}"/>`,
    );
  }

  domains.forEach((domain, index) => {
    const spoke = layout[index];
    if (!spoke) return;
    const hue = wheelHues[index % wheelHues.length]!;
    const outer = radiusForScore(domain.score, HUB_RADIUS, RIM_RADIUS);

    parts.push(
      `<path d="${petalPath(CENTRE, CENTRE, HUB_RADIUS, outer, spoke)}" fill="${hue}" fill-opacity="0.82" stroke="${hue}"/>`,
    );

    if (showTargets) {
      parts.push(
        `<path d="${arcPath(CENTRE, CENTRE, radiusForScore(domain.target, HUB_RADIUS, RIM_RADIUS), spoke)}" fill="none" stroke="${theme.textLo}" stroke-width="2" stroke-dasharray="4 4" stroke-linecap="round" opacity="0.8"/>`,
      );
    }

    const place = labelPlacement(CENTRE, CENTRE, WHEEL_LABEL_RADIUS, spoke);
    parts.push(
      `<text x="${place.x}" y="${place.y}" text-anchor="${place.anchor}" dominant-baseline="middle" font-family="system-ui, sans-serif" font-size="11" fill="${theme.textLo}">${escapeXml(shortLabel(domain.domain))} <tspan fill="${theme.textHi}" font-weight="600">${Math.round(domain.score)}</tspan></text>`,
    );
  });

  parts.push(
    `<circle cx="${CENTRE}" cy="${CENTRE}" r="${HUB_RADIUS}" fill="${theme.surface}" stroke="${theme.border}"/>`,
    `<text x="${CENTRE}" y="${CENTRE - 2}" text-anchor="middle" font-family="ui-monospace, monospace" font-size="30" font-weight="600" fill="${theme.textHi}">${average === null ? '—' : average.toFixed(1)}</text>`,
    `<text x="${CENTRE}" y="${CENTRE + 18}" text-anchor="middle" font-family="system-ui, sans-serif" font-size="11" letter-spacing="1" fill="${theme.textLo}">AVERAGE</text>`,
    '</g>',
  );

  // Wordmark — subtle, per the Share Kit brief.
  parts.push(
    `<text x="${CENTRE}" y="${height - 16}" text-anchor="middle" font-family="system-ui, sans-serif" font-size="10" letter-spacing="2.4" fill="${theme.accent}" opacity="0.85">COACH MILLA WELLNESS</text>`,
  );

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">${parts.join('')}</svg>`;
}

/** Rasterises the SVG. Returns a PNG blob at `pixels` on the long edge. */
export async function wheelPngBlob(options: WheelExportOptions): Promise<Blob> {
  const markup = wheelSvgMarkup(options);
  const pixels = options.pixels ?? 1080;

  // A data URL rather than a blob URL: an <img> loading a blob URL taints the
  // canvas in some WebViews, and a tainted canvas cannot be exported.
  // The UTF-8 round-trip matters — domain names carry "&" and non-ASCII.
  const utf8 = new TextEncoder().encode(markup);
  let binary = '';
  for (const byte of utf8) binary += String.fromCharCode(byte);
  const source = `data:image/svg+xml;base64,${btoa(binary)}`;

  const image = new Image();
  image.decoding = 'sync';
  await new Promise<void>((resolve, reject) => {
    image.onload = () => resolve();
    image.onerror = () => reject(new Error('Could not render the wheel for export.'));
    image.src = source;
  });

  const ratio = image.height / image.width || 1;
  const canvas = document.createElement('canvas');
  canvas.width = pixels;
  canvas.height = Math.round(pixels * ratio);

  const context = canvas.getContext('2d');
  if (!context) throw new Error('This browser will not give us a canvas to draw on.');
  context.drawImage(image, 0, 0, canvas.width, canvas.height);

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error('Could not encode the PNG.'));
    }, 'image/png');
  });
}

/** Saves a blob to disk. The one place a download is triggered. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  // Revoked on the next tick so the click has taken effect first.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function downloadText(text: string, filename: string, type = 'application/json'): void {
  downloadBlob(new Blob([text], { type }), filename);
}

function shortLabel(domain: string): string {
  const shortened: Record<string, string> = {
    'Romance/Partner': 'Romance',
    'Personal Growth': 'Growth',
    'Fun & Recreation': 'Fun',
    'Physical Environment': 'Environment',
    'Friends & Community': 'Friends',
    'Spirituality/Purpose': 'Purpose',
  };
  return shortened[domain] ?? domain;
}

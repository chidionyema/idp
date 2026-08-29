// The estate's palette, named once. Every module that paints (the sidebar mark, the
// wordmark, the home page pills) imports these; no other file carries a colour literal
// (crew#459 audit, 2026-08-29: three files duplicated the accent).
export const accent = '#e0762a';
export const accentSoft = '#f2b64b';
export const navy = '#141a26';
export const navyRaised = '#1c2433';
export const paperWarm = '#f6f4ef';
export const inkOnAccent = navy;
export const inkOnNavy = '#f5f1e8';

// The only colours that mean something (crew#612 CP4). Down is red, up is green, stale
// is the accent, not checked is grey.
export const statusLight = {
  ok: '#2e7d32',
  warning: '#b85a1c',
  error: '#c62828',
  pending: '#6b7280',
  running: '#2b3a55',
  aborted: '#6b7280',
};
export const statusDark = {
  ...statusLight,
  ok: '#4caf50',
  warning: '#f2a33c',
  error: '#ef5350',
  pending: '#9aa3b2',
};

// System faces first: the portal must look native on the founder's phone and a buyer's
// laptop without a font download that a proxy or a slow link can drop.
export const fontFamily =
  '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Inter, Roboto, "Helvetica Neue", Arial, sans-serif';
export const phone = '@media (max-width: 600px)';

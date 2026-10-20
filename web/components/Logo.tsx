import Link from "next/link";

// The mark is a meridian: a ring (the horizon), the line of longitude through it, and a
// bead where the two meet at the top — the meridian's summit, which is what the name means.
// It is drawn from three primitives at three fixed ratios (lens rx 0.44 of the ring radius,
// stroke 0.174, bead 0.2) so the nav's 22px mark and the 32px favicon are the same drawing at
// different sizes, not two drawings that drifted. Ring and lens take currentColor, so the mark
// inherits the lockup's colour and the whole logo turns accent on hover like every other link;
// the bead is the only filled shape, and it is the accent.
//
// The wordmark stays DM Mono: the site is serif for voice (headlines) and mono for labels
// (nav, tags, metrics), and the logo is a label. The accent period is kept from the old
// lockup — the bead and the period are the same mark at two scales, which is the rhythm the
// identity was missing when the period was the whole logo.

type Tone = "ink" | "light";

const RING_R = 8.6;
const LENS_RX = 3.8;
const STROKE = 1.5;
const BEAD_R = 1.7;

export function LogoMark({ size = 22, tone = "ink" }: { size?: number; tone?: Tone }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className="logo-mark"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="12" r={RING_R} stroke="currentColor" strokeWidth={STROKE} />
      <ellipse cx="12" cy="12" rx={LENS_RX} ry={RING_R} stroke="currentColor" strokeWidth={STROKE} />
      <circle cx="12" cy={12 - RING_R} r={BEAD_R} fill={tone === "light" ? "var(--accent-on-ink)" : "var(--accent)"} />
    </svg>
  );
}

export function Logo({ tone = "ink", size = 22 }: { tone?: Tone; size?: number }) {
  return (
    <Link href="/" className={`logo${tone === "light" ? " logo-light" : ""}`} aria-label="Meridian Intelligence — home">
      <LogoMark size={size} tone={tone} />
      <span className="logo-word">Meridian<span className="logo-dot">.</span></span>
    </Link>
  );
}

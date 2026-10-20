import type { Metadata } from "next";

/* A review surface, not a page of the site: four marks, at the sizes a mark actually has to work
   at, on both grounds, next to the wordmark they lock up with. The founder's review called the
   current mark a placeholder ("a circle with a line through it"). A logo is the one thing on this
   site that cannot be reviewed by reading a diff, so the candidates are put where he can look at
   them instead of described in prose. Pick one; the winner replaces the drawing in Logo.tsx,
   favicon.svg and opengraph-image.tsx. Not linked, not in the sitemap, noindex. */

export const metadata: Metadata = {
  title: "Mark candidates",
  robots: { index: false, follow: false },
};

const INK = "#0D0D0A";
const PAPER = "#FAFAF8";
const ACCENT = "#0E6E62";
const ACCENT_ON_INK = "#6FD3C2";

type MarkProps = { size: number; ink?: string; accent?: string; paper?: string };

/* A -- the shipped mark. Ring, meridian lens, bead. The circle is what reads as generic. */
function MarkA({ size, ink = INK, accent = ACCENT, paper = PAPER }: MarkProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="8.6" stroke={ink} strokeWidth="1.5" />
      <ellipse cx="12" cy="12" rx="3.8" ry="8.6" stroke={ink} strokeWidth="1.5" />
      <circle cx="12" cy="3.4" r="1.7" fill={accent} stroke={paper} strokeWidth="1" />
    </svg>
  );
}

/* B -- the seam. Two rules of unequal weight, a section through something. No curve at all, so it
   is the one candidate that survives 16px, engraving, and a single-colour favicon unchanged. */
function MarkB({ size, ink = INK, accent = ACCENT }: MarkProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="7.1" y="3.5" width="1.4" height="17" fill={ink} />
      <rect x="14.4" y="3.5" width="2.5" height="12.2" fill={ink} />
      <rect x="14.4" y="18.1" width="2.5" height="2.4" fill={accent} />
    </svg>
  );
}

/* C -- the cut. A filled tile with the meridian cut out of it off-centre, so the mark is one solid
   shape at any size and the line is negative space. Ownable, and it is not a circle. */
function MarkC({ size, ink = INK, accent = ACCENT }: MarkProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M3 3h18v18H3z" fill={ink} />
      <rect x="13.1" y="3" width="2.6" height="13.4" fill={PAPER} />
      <rect x="13.1" y="18.6" width="2.6" height="2.4" fill={accent} />
    </svg>
  );
}

/* D -- the plumb. A weighted line: the drawing is straight and the only mass is the bead at the
   bottom, which is what "meridian" means physically -- the line that drops. */
function MarkD({ size, ink = INK, accent = ACCENT }: MarkProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="10.9" y="2.6" width="2.2" height="10.4" fill={ink} />
      <circle cx="12" cy="17.2" r="3.4" fill={accent} />
      <circle cx="12" cy="17.2" r="1.15" fill={PAPER} />
    </svg>
  );
}

const CANDIDATES = [
  {
    key: "A",
    name: "Ring",
    mark: MarkA,
    note: "The mark that shipped. Correct, and a circle with a line through it is what it looks like.",
  },
  {
    key: "B",
    name: "Seam",
    mark: MarkB,
    note: "Two rules of unequal weight. No curve, so it holds at 16px and in one ink. The bead marks the section.",
  },
  {
    key: "C",
    name: "Cut",
    mark: MarkC,
    note: "A solid tile with the meridian cut out off-centre. One mass, negative space doing the drawing.",
  },
  {
    key: "D",
    name: "Plumb",
    mark: MarkD,
    note: "The meridian as a plumb line: straight drawing, all the weight in the bead.",
  },
];

const SIZES = [140, 64, 32, 16];

export default function LogoLab() {
  return (
    <main style={{ padding: "64px 0 96px" }}>
      <div className="container">
        <p style={{ fontFamily: "var(--mono)", fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--ink-3)" }}>
          Meridian — mark candidates
        </p>
        <h1 style={{ marginTop: "12px", maxWidth: "30ch" }}>Four marks, four sizes, two grounds.</h1>
        <p style={{ marginTop: "16px", color: "var(--ink-3)" }}>
          Pick one by letter and it becomes the drawing everywhere — navigation, favicon, link preview.
          They are shown at the sizes the mark actually has to survive, next to the wordmark it locks up with.
        </p>

        <div style={{ marginTop: "56px", display: "grid", gap: "1px", background: "var(--rule)" }}>
          {CANDIDATES.map((c) => {
            const Mark = c.mark;
            return (
              <div key={c.key} style={{ background: "var(--white)", padding: "32px 0" }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: "16px", flexWrap: "wrap" }}>
                  <span style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)", width: "18px" }}>{c.key}</span>
                  <span style={{ fontFamily: "var(--sans)", fontSize: "15px", fontWeight: 600, letterSpacing: "-0.02em", width: "88px" }}>{c.name}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: "40px", flexWrap: "wrap" }}>
                    {SIZES.map((s) => (
                      <div key={s} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
                        <Mark size={s} />
                        <span style={{ fontFamily: "var(--mono)", fontSize: "10px", color: "var(--ink-3)" }}>{s}</span>
                      </div>
                    ))}
                    <div style={{ display: "flex", alignItems: "center", gap: "9px", paddingLeft: "24px", borderLeft: "1px solid var(--rule)" }}>
                      <Mark size={22} />
                      <span style={{ fontFamily: "var(--sans)", fontSize: "17px", fontWeight: 600, letterSpacing: "-0.022em" }}>Meridian<span style={{ color: "var(--accent)" }}>.</span></span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "9px", background: INK, padding: "12px 16px" }}>
                      <Mark size={22} ink={PAPER} accent={ACCENT_ON_INK} />
                      <span style={{ fontFamily: "var(--sans)", fontSize: "17px", fontWeight: 600, letterSpacing: "-0.022em", color: "#fff" }}>Meridian<span style={{ color: ACCENT_ON_INK }}>.</span></span>
                    </div>
                  </div>
                </div>
                <p style={{ marginTop: "16px", marginLeft: "34px", maxWidth: "62ch", fontSize: "14px", color: "var(--ink-3)" }}>{c.note}</p>
              </div>
            );
          })}
        </div>

        <p style={{ marginTop: "40px", fontFamily: "var(--mono)", fontSize: "11px", color: "var(--ink-3)" }}>
          Reply with a letter. No letter means A stays.
        </p>
      </div>
    </main>
  );
}

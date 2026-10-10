// The front page's research card: what the estate's research department verified, newest
// first (idp#5714). The department runs hourly (namespace research) and writes to the
// estate's own Postgres; until 2026-10-10 the only way to read a claim was kubectl and psql,
// which is not a surface (founder, live). Three states, each in its own words: an
// unreachable department says so -- it never renders as "no findings", because an outage is
// not an empty desk (DESIGN-RULES 11).
import { useResearch } from './useResearch';

const TONE: Record<string, string> = {
  verified: '#7fd1b9',
  failed: '#ff6b81',
  rejected: '#ff6b81',
};

function toneOf(status: string): string {
  const s = status.toLowerCase();
  if (s.includes('verif')) return TONE.verified;
  if (s.includes('fail') || s.includes('reject')) return TONE.failed;
  return 'rgba(232,237,245,0.72)';
}

function ago(iso: string, nowMs: number): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return 'at an unknown time';
  const s = Math.max(0, Math.round((nowMs - t) / 1000));
  if (s < 90) return 'just now';
  if (s < 5400) return `${Math.round(s / 60)} min ago`;
  if (s < 2 * 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

export function ResearchCard() {
  const loaded = useResearch(3);
  const now = Date.now();
  return (
    <section
      data-testid="research-card"
      style={{
        margin: '40px auto 0',
        maxWidth: 960,
        padding: '16px 20px',
        borderRadius: 14,
        border: '1px solid rgba(232,237,245,0.14)',
        background: 'rgba(255,255,255,0.03)',
      }}
    >
      <h2
        style={{
          margin: 0,
          fontSize: 17,
          fontWeight: 600,
          color: '#1a1a1a',
        }}
      >
        What research found
      </h2>
      <p style={{ margin: '4px 0 12px', fontSize: 14, color: 'rgba(0,0,0,0.6)' }}>
        The research department answers one question an hour and records what it verified.
      </p>
      {loaded.state === 'loading' ? (
        <p data-testid="research-loading" style={{ margin: 0, fontSize: 14, color: 'rgba(0,0,0,0.55)' }}>
          Reading the research department…
        </p>
      ) : loaded.state === 'error' ? (
        <p data-testid="research-error" style={{ margin: 0, fontSize: 14, color: '#b3261e' }}>
          The research department could not be read: {loaded.error}
        </p>
      ) : loaded.claims.length === 0 ? (
        <p data-testid="research-empty" style={{ margin: 0, fontSize: 14, color: 'rgba(0,0,0,0.55)' }}>
          No findings yet. The engine's first hourly run puts the first one here.
        </p>
      ) : (
        <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
          {loaded.claims.map((claim, i) => (
            <li
              key={i}
              data-testid="research-claim"
              style={{
                padding: '8px 0',
                borderTop: i === 0 ? 'none' : '1px solid rgba(0,0,0,0.08)',
                fontSize: 14,
                lineHeight: 1.45,
                color: '#1a1a1a',
              }}
            >
              {claim.statement}
              <span
                style={{
                  marginLeft: 8,
                  fontSize: 12,
                  fontWeight: 600,
                  letterSpacing: '0.04em',
                  textTransform: 'uppercase',
                  color: toneOf(claim.status),
                }}
              >
                {claim.status || 'unlabelled'} · {ago(claim.created_at, now)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

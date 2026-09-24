// crew#973 CP2: the Deploy River page (/river).
//
// The estate's Definition of Done rendered as a river of commits: each commit travels
// through gates (push → auto-PR → fast-gate → crucible → merge → build-multiarch →
// trivy → cosign → flux reflector → image-automation → deploy-when-green → reconcile →
// pod ready → first production log line).
//
// Data: `GET /api/fleetview/journeys` from the fleetview backend, reading
// deploy_journeys / deploy_journey_events written by bin/estate-deploy-recorder.
// A journey with no rows means the recorder has not run yet -- stated plainly,
// never invented as an empty river.
//
// CP2 done means: a live push visibly flies through the gates; a forced failure
// visibly cracks its gate. The river metaphor and stage states are real here;
// the Three.js WebGL scene (the full 2100 spec) is CP2+ work.
import { useCallback, useEffect, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import Box from '@material-ui/core/Box';
import Chip from '@material-ui/core/Chip';
import Divider from '@material-ui/core/Divider';
import Paper from '@material-ui/core/Paper';
import Typography from '@material-ui/core/Typography';
import { makeStyles } from '@material-ui/core/styles';
import { EstatePage, Section, Unread, Waiting } from '../shell';

// ─── Types ────────────────────────────────────────────────────────────────────

export type JourneyEvent = {
  seq: number;
  stage: string;
  status: 'pass' | 'fail' | 'pending' | 'unknown';
  detail: Record<string, unknown>;
  ts: string | null;
};

export type Journey = {
  sha: string;
  branch: string | null;
  pr_number: number | null;
  title: string | null;
  state: 'merged' | 'in_flight' | 'failed' | 'abandoned';
  started_at: string | null;
  merged_at: string | null;
  events: JourneyEvent[];
};

export type JourneysEnvelope = {
  available: boolean;
  error: string | null;
  journeys: Journey[];
  generated_at: string;
};

export const TITLE = 'Deploy River';
export const LEAD =
  'Every commit on its road from push to cluster. A green ring means the gate passed; a cracked ring means it failed. The journey is done only when the pod is serving.';

// ─── Gate labels ──────────────────────────────────────────────────────────────

const GATE_LABEL: Record<string, string> = {
  pr_opened: 'PR opened',
  merged: 'Merged',
  'check:idp-ci': 'CI',
  'check:fast-gate': 'Fast gate',
  'check:bdd': 'BDD',
  'check:security-scan': 'Sec scan',
  'check:': 'Checks',
  'build-multiarch': 'Build',
  trivy: 'Trivy',
  cosign: 'Cosign',
  'flux-reflector': 'Flux sync',
  'image-automation': 'Img update',
  'deploy-when-green': 'Deploy',
  reconcile: 'Reconcile',
  'pod-ready': 'Pod ready',
  'first-log': 'Serving',
};

const shortLabel = (stage: string): string => {
  if (GATE_LABEL[stage]) return GATE_LABEL[stage];
  if (stage.startsWith('check:')) return stage.slice(6);
  return stage;
};

// ─── State colours ────────────────────────────────────────────────────────────

const STATUS_COLOR: Record<string, string> = {
  pass: '#00cc88',
  fail: '#ff3366',
  pending: '#ffaa00',
  unknown: '#666680',
};

const STATE_COLOR: Record<string, string> = {
  merged: '#00cc88',
  in_flight: '#ffaa00',
  failed: '#ff3366',
  abandoned: '#666680',
};

const STATE_WORD: Record<string, string> = {
  merged: 'Live',
  in_flight: 'In flight',
  failed: 'Failed',
  abandoned: 'Abandoned',
};

// ─── Styles ───────────────────────────────────────────────────────────────────

const useStyles = makeStyles(theme => ({
  gateRing: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 32,
    height: 32,
    borderRadius: '50%',
    borderWidth: 2,
    borderStyle: 'solid',
    fontSize: '0.65rem',
    fontWeight: 700,
    flexShrink: 0,
  },
  chipLive: {
    backgroundColor: '#00cc88',
    color: '#fff',
    fontWeight: 700,
    fontSize: '0.65rem',
  },
  chipFailed: {
    backgroundColor: '#ff3366',
    color: '#fff',
    fontWeight: 700,
    fontSize: '0.65rem',
  },
  chipInFlight: {
    backgroundColor: '#ffaa00',
    color: '#fff',
    fontWeight: 700,
    fontSize: '0.65rem',
  },
  chipAbandoned: {
    backgroundColor: '#666680',
    color: '#fff',
    fontWeight: 700,
    fontSize: '0.65rem',
  },
  journeyRow: {
    padding: theme.spacing(2),
    marginBottom: theme.spacing(2),
    borderLeft: '4px solid',
  },
  andonStrip: {
    height: 6,
    borderRadius: 3,
    marginBottom: theme.spacing(3),
    opacity: 0.6,
  },
  emptyPaper: {
    padding: theme.spacing(3),
    textAlign: 'center' as const,
    border: '1px dashed #666',
  },
  mono: {
    fontFamily: 'monospace',
  },
}));

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useJourneys(limit = 30) {
  const fetchApi = useApi(fetchApiRef);
  const discovery = useApi(discoveryApiRef);
  const [envelope, setEnvelope] = useState<JourneysEnvelope | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const base = await discovery.getBaseUrl('proxy');
      const res = await fetchApi.fetch(`${base}/fleetview/journeys?limit=${limit}`);
      const body = (await res.json()) as JourneysEnvelope;
      setEnvelope(body);
    } catch (e) {
      setEnvelope({
        available: false,
        error: String(e),
        journeys: [],
        generated_at: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  }, [fetchApi, discovery, limit]);

  useEffect(() => {
    void refresh();
    const id = setInterval(() => { void refresh(); }, 30_000);
    return () => clearInterval(id);
  }, [refresh]);

  return { envelope, loading, refresh };
}

// ─── Gate ring ────────────────────────────────────────────────────────────────

function GateRing({ event }: { event: JourneyEvent }) {
  const classes = useStyles();
  const color = STATUS_COLOR[event.status] ?? STATUS_COLOR.unknown;
  const isCracked = event.status === 'fail';
  const isPending = event.status === 'pending';
  return (
    <span
      className={classes.gateRing}
      style={{
        borderColor: color,
        backgroundColor: event.status === 'pass' ? color : 'transparent',
        color,
        opacity: isPending ? 0.5 : 1,
        borderStyle: isCracked ? 'dashed' : 'solid',
      }}
      title={`${event.stage}: ${event.status}${event.ts ? ` at ${event.ts}` : ''}`}
    >
      {isCracked ? '✕' : isPending ? '…' : '✓'}
    </span>
  );
}

// ─── Journey row ──────────────────────────────────────────────────────────────

function JourneyRow({ journey }: { journey: Journey }) {
  const classes = useStyles();
  const stateColor = STATE_COLOR[journey.state] ?? STATE_COLOR.abandoned;
  const shortSha = (journey.sha ?? '??????').slice(0, 7);

  const ago = journey.started_at
    ? (() => {
        const s = Math.max(
          0,
          Math.round(
            (Date.now() - new Date(journey.started_at).getTime()) / 1000,
          ),
        );
        if (s < 60) return `${s}s ago`;
        if (s < 3600) return `${Math.floor(s / 60)}m ago`;
        if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
        return `${Math.floor(s / 86400)}d ago`;
      })()
    : null;

  const chipClass =
    journey.state === 'merged'
      ? classes.chipLive
      : journey.state === 'failed'
        ? classes.chipFailed
        : journey.state === 'in_flight'
          ? classes.chipInFlight
          : classes.chipAbandoned;

  return (
    <Paper
      elevation={0}
      className={classes.journeyRow}
      style={{
        borderLeftColor: stateColor,
        background: journey.state === 'failed' ? 'rgba(255,51,102,0.04)' : undefined,
      }}
      data-testid={`journey-${shortSha}`}
    >
      <Box display="flex" alignItems="center" flexWrap="wrap" mb={1}>
        <Chip
          size="small"
          label={STATE_WORD[journey.state] ?? journey.state}
          className={chipClass}
        />
        <Box ml={1}>
          <Typography
            component="code"
            variant="caption"
            className={classes.mono}
            style={{ color: 'rgba(255,255,255,0.6)' }}
          >
            {shortSha}
          </Typography>
        </Box>
        {journey.branch && (
          <Box ml={1}>
            <Chip size="small" label={journey.branch} variant="outlined" />
          </Box>
        )}
        {journey.pr_number && (
          <Box ml={1}>
            <Typography variant="caption" color="textSecondary">
              PR #{journey.pr_number}
            </Typography>
          </Box>
        )}
        {ago && (
          <Box ml={1}>
            <Typography variant="caption" color="textSecondary">
              {ago}
            </Typography>
          </Box>
        )}
        <Box flex={1} />
        {journey.title && (
          <Typography
            variant="body2"
            style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              maxWidth: 400,
            }}
          >
            {journey.title}
          </Typography>
        )}
      </Box>

      {/* The river: one gate ring per event, left to right in sequence order */}
      <Box display="flex" flexWrap="wrap">
        {journey.events.length > 0 ? (
          journey.events.map(e => <GateRing key={`${e.seq}-${e.stage}`} event={e} />)
        ) : (
          <Typography
            variant="caption"
            color="textSecondary"
            style={{ fontStyle: 'italic' }}
          >
            No stage events recorded yet
          </Typography>
        )}
      </Box>

      {/* Stage labels below the rings */}
      {journey.events.length > 0 && (
        <Box display="flex" flexWrap="wrap" mt={0.5}>
          {journey.events.map(e => {
            const color = STATUS_COLOR[e.status] ?? STATUS_COLOR.unknown;
            return (
              <Box
                key={`${e.seq}-${e.stage}`}
                style={{
                  fontSize: '0.6rem',
                  color,
                  maxWidth: 50,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                title={e.stage}
              >
                {shortLabel(e.stage)}
              </Box>
            );
          })}
        </Box>
      )}
    </Paper>
  );
}

// ─── Andon mood ──────────────────────────────────────────────────────────────

function AndonStrip({ journeys }: { journeys: Journey[] }) {
  const classes = useStyles();
  const hasFailure = journeys.some(j => j.state === 'failed');
  const hasInFlight = journeys.some(j => j.state === 'in_flight');
  const moodColor = hasFailure ? '#ffaa00' : hasInFlight ? '#3399ff' : '#00cc88';
  const moodLabel = hasFailure
    ? 'A commit is failing'
    : hasInFlight
      ? 'Commits are in flight'
      : 'All recent commits are live';
  return (
    <div
      className={classes.andonStrip}
      style={{ background: moodColor }}
      title={moodLabel}
      data-testid="river-andon-strip"
    />
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function River() {
  const classes = useStyles();
  const { envelope, loading } = useJourneys();

  return (
    <EstatePage title={TITLE} lead={LEAD}>
      <Section title="The river" blurb="Every push, every gate, every merge. Refreshes every 30 seconds." testId="river-main">
        {loading && !envelope && (
          <Waiting testId="river-loading">Reading the deploy ledger.</Waiting>
        )}

        {!loading && envelope && !envelope.available && (
          <Unread testId="river-error" detail={envelope.error ?? 'unknown'}>
            The deploy store could not be read.
          </Unread>
        )}

        {envelope && envelope.available && (
          <>
            <AndonStrip journeys={envelope.journeys} />

            <Typography variant="body2" color="textSecondary" style={{ marginBottom: 16 }}>
              {envelope.journeys.length === 0
                ? 'No journeys recorded yet. Run bin/estate-deploy-recorder to populate the ledger.'
                : `${envelope.journeys.length} commit${envelope.journeys.length === 1 ? '' : 's'} in the ledger.`}
            </Typography>

            {/* Gate legend */}
            <Box display="flex" flexWrap="wrap" alignItems="center" mb={2}>
              <Typography variant="overline" style={{ marginRight: 8 }}>
                Gate key:
              </Typography>
              {([
                { status: 'pass', label: 'Passed' },
                { status: 'fail', label: 'Failed' },
                { status: 'pending', label: 'Pending' },
                { status: 'unknown', label: 'Unknown' },
              ] as const).map(({ status, label }) => (
                <Box
                  key={status}
                  display="flex"
                  alignItems="center"
                  style={{ marginRight: 12 }}
                >
                  <Box
                    style={{
                      width: 14,
                      height: 14,
                      borderRadius: '50%',
                      borderWidth: 2,
                      borderStyle: 'solid',
                      borderColor: STATUS_COLOR[status],
                      background:
                        status === 'pass' ? STATUS_COLOR[status] : 'transparent',
                      marginRight: 4,
                    }}
                  />
                  <Typography variant="caption">{label}</Typography>
                </Box>
              ))}
            </Box>

            <Divider style={{ marginBottom: 16 }} />

            {/* Journey list, newest first */}
            {envelope.journeys.length === 0 ? (
              <Paper elevation={0} className={classes.emptyPaper}>
                <Typography
                  color="textSecondary"
                  style={{ fontStyle: 'italic' }}
                >
                  The ledger is empty. No commits have been recorded yet.
                </Typography>
                <Typography
                  variant="caption"
                  color="textSecondary"
                  display="block"
                  style={{ marginTop: 8 }}
                >
                  Run{' '}
                  <code>bin/estate-deploy-recorder</code> to record the first
                  journeys.
                </Typography>
              </Paper>
            ) : (
              envelope.journeys.map(j => (
                <JourneyRow key={j.sha} journey={j} />
              ))
            )}
          </>
        )}
      </Section>
    </EstatePage>
  );
}

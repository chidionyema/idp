// crew#973 CP2+CP3+CP4: the Deploy River page (/river).
//
// CP2: The estate's Definition of Done rendered as a river of commits: each commit travels
// through gates (push → CI → fast-gate → crucible → merge → build → trivy → cosign →
// flux reflector → image-automation → deploy-when-green → reconcile → pod ready).
//
// CP3: Narration engine — SSE tail from the backend, with ambient narration mode.
// When on, the voice engine speaks each transition as it arrives. Story mode speaks
// a commit's full journey when you focus it. No LLM narrates: templates over the
// ledger, deterministic from real timestamps.
//
// CP4: Time-scrub slider — replay the river at any point in the last 4 hours.
// Gate holograms — hover a ring to see its detail. "Ask Holmes" on a cracked gate
// — interrogate the estate's investigator about what went wrong.
//
// Data: `GET /fleetview/journeys` (all events) and `GET /fleetview/journeys/at?as_of=ISO`
// (time-scrubbed).  SSE stream: `GET /fleetview/journeys/stream` tails new events.
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import Box from '@material-ui/core/Box';
import Button from '@material-ui/core/Button';
import Chip from '@material-ui/core/Chip';
import CircularProgress from '@material-ui/core/CircularProgress';
import Divider from '@material-ui/core/Divider';

import Paper from '@material-ui/core/Paper';
import Slider from '@material-ui/core/Slider';
import Tooltip from '@material-ui/core/Tooltip';
import Typography from '@material-ui/core/Typography';
import { makeStyles } from '@material-ui/core/styles';
import BugReport from '@material-ui/icons/BugReport';
import InfoOutlined from '@material-ui/icons/InfoOutlined';
import VolumeUp from '@material-ui/icons/VolumeUp';
import VolumeOff from '@material-ui/icons/VolumeOff';
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
  as_of?: string;
};

export type JourneyFrame = {
  sha: string;
  state: string;
  last_event: JourneyEvent | null;
  narration: string;
  story: string;
};

export const TITLE = 'Deploy River';
export const LEAD =
  'Every commit on its road from push to cluster. Green ring: passed. Cracked ring: failed. Hover a ring for the hologram. Click a cracked ring to ask Holmes.';

// ─── Gate labels ──────────────────────────────────────────────────────────────

const GATE_LABEL: Record<string, string> = {
  pr_opened: 'PR open',
  merged: 'Merge',
  'check:idp-ci': 'CI',
  'check:fast-gate': 'Fast gate',
  'check:bdd': 'BDD',
  'check:bdd-suites': 'BDD suites',
  'check:bdd-suites (acceptance)': 'BDD accept',
  'check:bdd-suites (tests)': 'BDD tests',
  'check:security-scan': 'Sec scan',
  'check:': 'Check',
  'check:merge': 'Merge gate',
  'check:build': 'Build',
  'check:build (idp, Dockerfile, ., linux/arm64)': 'Build arm64',
  'check:build (idp, Dockerfile, ., linux/amd64)': 'Build amd64',
  'check:build (sovereign-worker': 'Worker build',
  'check:publish': 'Publish',
  'check:publish-to-state-branch': 'Publish state',
  'check:discover': 'Discover',
  'check:executes-gate': 'Executes',
  'check:feature-request-plan': 'Feature plan',
  'check:guarded-paths': 'Guarded paths',
  'check:offline-gate': 'Offline',
  'check:migrate-domain': 'Migrate',
  'check:messaging-demo': 'Messaging',
  'check:estate-graph-sync': 'Graph sync',
  'check:shadow-verify': 'Shadow verify',
  'check:test': 'Test',
  'check:verifier': 'Verifier',
  'check:verifier / verifier': 'Verifier',
  'check:fast-gate / fast-gate': 'Fast gate',
  'check:ruff-required': 'Ruff',
  'check:portal-app': 'Portal app',
  'check:check': 'Check',
  'check:open': 'Open',
  'check:land': 'Land',
  'check:verify': 'Verify',
  'check:prove': 'Prove',
  'check:hydrate': 'Hydrate',
  'check:k3s': 'K3s',
  'check:apply': 'Apply',
  'check:bin/idp-root-trust': 'Root trust',
  'check:plain-english': 'Plain english',
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
  if (stage.startsWith('check:')) {
    const name = stage.slice(6);
    if (name.includes('(')) return name.split('(')[0].trim();
    return name;
  }
  return stage.length > 8 ? stage.slice(0, 8) + '…' : stage;
};

const fullLabel = (stage: string): string => GATE_LABEL[stage] || stage;

// ─── State colours ────────────────────────────────────────────────────────────

const STATUS_COLOR: Record<string, string> = {
  pass: '#00cc88',
  fail: '#ff3366',
  pending: '#ffaa00',
  unknown: '#666680',
  cancelled: '#888899',
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
    width: 34,
    height: 34,
    borderRadius: '50%',
    borderWidth: 2,
    borderStyle: 'solid',
    fontSize: '0.6rem',
    fontWeight: 700,
    flexShrink: 0,
    cursor: 'default',
    transition: 'transform 0.1s',
    '&:hover': { transform: 'scale(1.2)' },
  },
  gateRingClickable: {
    cursor: 'pointer',
    '&:hover': { transform: 'scale(1.2)' },
  },
  chipLive: {
    backgroundColor: '#00cc88',
    color: '#fff',
    fontWeight: 700,
    fontSize: '0.6rem',
  },
  chipFailed: {
    backgroundColor: '#ff3366',
    color: '#fff',
    fontWeight: 700,
    fontSize: '0.6rem',
  },
  chipInFlight: {
    backgroundColor: '#ffaa00',
    color: '#000',
    fontWeight: 700,
    fontSize: '0.6rem',
  },
  chipAbandoned: {
    backgroundColor: '#666680',
    color: '#fff',
    fontWeight: 700,
    fontSize: '0.6rem',
  },
  journeyRow: {
    padding: theme.spacing(2),
    marginBottom: theme.spacing(2),
    borderLeft: '4px solid',
    transition: 'background 0.2s',
  },
  andonStrip: {
    height: 6,
    borderRadius: 3,
    marginBottom: theme.spacing(3),
    opacity: 0.7,
  },
  emptyPaper: {
    padding: theme.spacing(3),
    textAlign: 'center' as const,
    border: '1px dashed #666',
  },
  mono: { fontFamily: 'monospace' },
  holmesPanel: {
    padding: theme.spacing(2),
    marginBottom: theme.spacing(2),
    background: 'rgba(255,51,102,0.06)',
    border: '1px solid rgba(255,51,102,0.3)',
    borderRadius: 4,
  },
  scrubLabel: {
    fontSize: '0.7rem',
    color: 'rgba(255,255,255,0.5)',
    fontFamily: 'monospace',
  },
}));

// ─── Hook: journeys data ─────────────────────────────────────────────────────

function useJourneys(limit = 30, asOf?: string) {
  const fetchApi = useApi(fetchApiRef);
  const discovery = useApi(discoveryApiRef);
  const [envelope, setEnvelope] = useState<JourneysEnvelope | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const base = await discovery.getBaseUrl('proxy');
      const url = asOf
        ? `${base}/fleetview/journeys/at?as_of=${encodeURIComponent(asOf)}`
        : `${base}/fleetview/journeys?limit=${limit}`;
      const res = await fetchApi.fetch(url);
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
  }, [fetchApi, discovery, limit, asOf]);

  useEffect(() => { void refresh(); }, [refresh]);

  return { envelope, loading, refresh };
}

// ─── Hook: SSE narration stream ───────────────────────────────────────────────

export function useJourneysStream(opts: {
  speakFn?: (text: string) => void;
  narrationOn: boolean;
  onStory?: (sha: string, story: string) => void;
}) {
  const { speakFn, narrationOn, onStory } = opts;
  const discovery = useApi(discoveryApiRef);
  const esRef = useRef<EventSource | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastFrame, setLastFrame] = useState<JourneyFrame | null>(null);
  const lastShaRef = useRef<string | null>(null);
  const speakFnRef = useRef(speakFn);
  const narrationOnRef = useRef(narrationOn);
  const onStoryRef = useRef(onStory);
  speakFnRef.current = speakFn;
  narrationOnRef.current = narrationOn;
  onStoryRef.current = onStory;

  const connect = useCallback(async () => {
    const base = await discovery.getBaseUrl('proxy');
    const url = `${base}/fleetview/journeys/stream`;
    const es = new EventSource(url);
    esRef.current = es;
    setConnected(true);
    es.onmessage = (e: MessageEvent) => {
      if (!e.data || e.data.startsWith(':')) return;
      try {
        const frame = JSON.parse(e.data) as JourneyFrame;
        if (!frame || !frame.narration) return;
        if (lastShaRef.current === frame.sha) return;
        lastShaRef.current = frame.sha;
        setLastFrame(frame);
        if (narrationOnRef.current && speakFnRef.current && frame.narration) {
          speakFnRef.current(frame.narration);
        }
        if (onStoryRef.current && frame.story) {
          onStoryRef.current(frame.sha, frame.story);
        }
      } catch { /* malformed */ }
    };
    es.onerror = () => {
      setConnected(false);
      es.close();
      esRef.current = null;
      setTimeout(() => { void connect(); }, 5000);
    };
  }, [discovery]);

  useEffect(() => {
    void connect();
    return () => {
      esRef.current?.close();
      esRef.current = null;
      setConnected(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connect]);
  return { connected, lastFrame };
}

// ─── Gate ring ────────────────────────────────────────────────────────────────

interface GateRingProps {
  event: JourneyEvent;
  onHolmes?: (event: JourneyEvent) => void;
}

function GateRing({ event, onHolmes }: GateRingProps) {
  const classes = useStyles();
  const color = STATUS_COLOR[event.status] ?? STATUS_COLOR.unknown;
  const isCracked = event.status === 'fail';
  const isPending = event.status === 'pending';
  const isCancelled = (event.status as string) === 'cancelled';

  const icon =
    isCracked ? '✕' :
    isPending  ? '…' :
    isCancelled ? '—' :
                 '✓';

  const detail = event.detail as Record<string, string | number | null>;
  const conclusion = detail?.conclusion as string | undefined;
  const url = detail?.url as string | undefined;
  const tsLabel = event.ts
    ? (() => {
        try {
          const d = new Date(event.ts);
          return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
        } catch { return event.ts; }
      })()
    : null;

  const tooltip = (
    <Box p={1} style={{ maxWidth: 280 }}>
      <Typography variant="caption" style={{ fontWeight: 700, color }} gutterBottom display="block">
        {fullLabel(event.stage)}
      </Typography>
      <Typography variant="caption" display="block" style={{ textTransform: 'capitalize' }}>
        {event.status}
        {conclusion && conclusion !== event.status ? `: ${conclusion}` : ''}
      </Typography>
      {tsLabel && (
        <Typography variant="caption" display="block" color="textSecondary">
          {tsLabel}
        </Typography>
      )}
      {url && (
        <Typography variant="caption" display="block" style={{ color: '#88aacc', wordBreak: 'break-all' }}>
          {url.replace('https://api.github.com/repos/chidionyema/idp/check-runs/', 'check-run/')}
        </Typography>
      )}
      {isCracked && (
        <Typography variant="caption" display="block" style={{ color: '#ff6699', marginTop: 4 }}>
          Click ring to ask Holmes
        </Typography>
      )}
    </Box>
  );

  return (
    <Tooltip title={tooltip} placement="top" arrow>
      <span
        className={`${classes.gateRing} ${isCracked && onHolmes ? classes.gateRingClickable : ''}`}
        style={{
          borderColor: color,
          backgroundColor: event.status === 'pass' ? color : 'transparent',
          color,
          opacity: isPending ? 0.5 : 1,
          borderStyle: isCracked || isCancelled ? 'dashed' : 'solid',
        }}
        onClick={isCracked && onHolmes ? () => onHolmes(event) : undefined}
        data-testid={`gate-${event.stage}`}
        role={isCracked ? 'button' : undefined}
      >
        {icon}
      </span>
    </Tooltip>
  );
}

// ─── Holmes interrogation ─────────────────────────────────────────────────────

function useAskHolmes() {
  const fetchApi = useApi(fetchApiRef);
  const discovery = useApi(discoveryApiRef);
  const [answer, setAnswer] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = useCallback(
    async (question: string) => {
      setAsking(true);
      setError(null);
      setAnswer(null);
      try {
        const base = await discovery.getBaseUrl('proxy');
        const res = await fetchApi.fetch(
          `${base}/fleetview/ask-holmes?q=${encodeURIComponent(question)}`,
        );
        const body = (await res.json()) as {
          answered: boolean;
          analysis: string;
          error: string | null;
        };
        if (body.answered) {
          setAnswer(body.analysis);
        } else {
          setError(body.error ?? 'Holmes could not answer');
        }
      } catch (e) {
        setError(String(e));
      } finally {
        setAsking(false);
      }
    },
    [fetchApi, discovery],
  );

  return { answer, error, asking, ask };
}

// ─── Time scrub ────────────────────────────────────────────────────────────────

interface TimeScrubProps {
  onChange: (asOf: string | undefined) => void;
  currentAsOf: string | undefined;
}

function TimeScrub({ onChange, currentAsOf }: TimeScrubProps) {
  const classes = useStyles();
  const [now] = useState(() => Date.now());
  // Window: last 4 hours, 30-minute steps
  const MIN_MS = now - 4 * 60 * 60 * 1000;
  const STEP_MS = 30 * 60 * 1000;

  const currentMs = currentAsOf
    ? new Date(currentAsOf).getTime()
    : now;

  // Slider goes 0 (= 4h ago) to 100 (= now)
  const sliderVal = Math.round((currentMs - MIN_MS) / (now - MIN_MS) * 100);

  const handleChange = (_: unknown, val: number | number[]) => {
    const pct = (val as number) / 100;
    const ms = MIN_MS + pct * (now - MIN_MS);
    const rounded = Math.round(ms / STEP_MS) * STEP_MS;
    if (rounded >= now - 60_000) {
      onChange(undefined); // live
    } else {
      onChange(new Date(rounded).toISOString().replace('Z', '+00:00'));
    }
  };

  const displayTime = currentAsOf
    ? (() => {
        try {
          const d = new Date(currentAsOf);
          const now2 = new Date();
          const diffS = Math.round((now2.getTime() - d.getTime()) / 1000);
          if (diffS < 60) return `${diffS}s ago`;
          if (diffS < 3600) return `${Math.floor(diffS / 60)}m ago`;
          return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
        } catch { return currentAsOf; }
      })()
    : 'LIVE';

  return (
    <Box display="flex" alignItems="center" style={{ gap: 8 }} mb={2}>
      <Typography variant="caption" className={classes.scrubLabel}>4h ago</Typography>
      <Slider
        value={sliderVal}
        onChange={handleChange}
        min={0}
        max={100}
        step={1}
        style={{ width: 200, color: currentAsOf ? '#ffaa00' : '#00cc88' }}
        data-testid="river-time-scrub"
      />
      <Typography variant="caption" className={classes.scrubLabel} style={{ color: currentAsOf ? '#ffaa00' : '#00cc88' }}>
        {displayTime}
      </Typography>
      {currentAsOf && (
        <Button
          size="small"
          variant="outlined"
          onClick={() => onChange(undefined)}
          style={{ fontSize: '0.65rem', padding: '2px 6px' }}
          data-testid="river-live-btn"
        >
          Return to live
        </Button>
      )}
    </Box>
  );
}

// ─── Journey row ──────────────────────────────────────────────────────────────

interface JourneyRowProps {
  journey: Journey;
  onStory?: (sha: string, story: string) => void;
  onHolmes?: (journey: Journey, event: JourneyEvent) => void;
}

function JourneyRow({ journey, onStory, onHolmes }: JourneyRowProps) {
  const classes = useStyles();
  const stateColor = STATE_COLOR[journey.state] ?? STATE_COLOR.abandoned;
  const shortSha = (journey.sha ?? '??????').slice(0, 7);
  const [storyText, setStoryText] = useState<string | null>(null);

  const ago = journey.started_at
    ? (() => {
        const s = Math.max(0, Math.round((Date.now() - new Date(journey.started_at).getTime()) / 1000));
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

  const handleStory = () => {
    if (storyText) { setStoryText(null); return; }
    const failCount = journey.events.filter(e => e.status === 'fail').length;
    const state = journey.state;
    const started = journey.started_at
      ? (() => {
          try {
            return new Date(journey.started_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
          } catch { return null; }
        })()
      : null;
    const merged = journey.merged_at
      ? (() => {
          try {
            return new Date(journey.merged_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
          } catch { return null; }
        })()
      : null;
    let story = `Commit ${shortSha}`;
    if (started) story += ` pushed ${started}`;
    if (failCount > 0) story += `, ${failCount} gate${failCount > 1 ? 's' : ''} failed first`;
    if (state === 'merged') {
      story += merged ? `, merged ${merged}, signed, rolled in, serving now` : ', merged, signed, rolled in, serving now';
    } else if (state === 'failed') {
      story += ', did not merge';
    } else if (state === 'abandoned') {
      story += ', abandoned';
    }
    setStoryText(story + '.');
    if (onStory) onStory(journey.sha, story + '.');
  };

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
      <Box display="flex" alignItems="center" flexWrap="wrap" mb={1} style={{ gap: 4 }}>
        <Chip size="small" label={STATE_WORD[journey.state] ?? journey.state} className={chipClass} />
        <Typography component="code" variant="caption" className={classes.mono} style={{ color: 'rgba(255,255,255,0.6)' }}>
          {shortSha}
        </Typography>
        {journey.branch && <Chip size="small" label={journey.branch} variant="outlined" />}
        {journey.pr_number && (
          <Typography variant="caption" color="textSecondary">PR #{journey.pr_number}</Typography>
        )}
        {ago && <Typography variant="caption" color="textSecondary">{ago}</Typography>}
        <Box flex={1} />
        {onStory && (
          <Button size="small" onClick={handleStory} style={{ fontSize: '0.65rem' }}>
            {storyText ? 'Close' : 'Hear it'}
          </Button>
        )}
        {journey.title && (
          <Typography variant="body2" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 280 }}>
            {journey.title}
          </Typography>
        )}
      </Box>

      {/* Story mode overlay */}
      {storyText && (
        <Box mb={1}>
          <Typography variant="body2" style={{ fontStyle: 'italic', color: '#00cc88' }}>
            {storyText}
          </Typography>
        </Box>
      )}

      {/* The river: one gate ring per event */}
      <Box display="flex" flexWrap="wrap">
        {journey.events.length > 0 ? (
          journey.events.map(e => (
            <GateRing
              key={`${e.seq}-${e.stage}`}
              event={e}
              onHolmes={onHolmes ? () => onHolmes(journey, e) : undefined}
            />
          ))
        ) : (
          <Typography variant="caption" color="textSecondary" style={{ fontStyle: 'italic' }}>
            No stage events recorded yet
          </Typography>
        )}
      </Box>

      {/* Stage labels */}
      {journey.events.length > 0 && (
        <Box display="flex" flexWrap="wrap" mt={0.5}>
          {journey.events.map(e => {
            const color = STATUS_COLOR[e.status] ?? STATUS_COLOR.unknown;
            return (
              <Box
                key={`${e.seq}-${e.stage}-lbl`}
                style={{
                  fontSize: '0.58rem',
                  color,
                  maxWidth: 44,
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
  const moodColor = hasFailure ? '#ff3366' : hasInFlight ? '#3399ff' : '#00cc88';
  const moodLabel = hasFailure
    ? 'A commit is failing — click a cracked ring to ask Holmes'
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
  const fetchApi = useApi(fetchApiRef);
  const discovery = useApi(discoveryApiRef);
  const [narrationOn, setNarrationOn] = useState(false);
  const [storyText, setStoryText] = useState<string | null>(null);
  const [storySha, setStorySha] = useState<string | null>(null);
  const [timeAsOf, setTimeAsOf] = useState<string | undefined>(undefined);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const { answer: holmesAnswer, error: holmesError, asking: holmesAsking, ask: askHolmes } = useAskHolmes();

  const { envelope, loading } = useJourneys(30, timeAsOf);

  const speak = useCallback(async (text: string) => {
    if (!text) return;
    try {
      const base = await discovery.getBaseUrl('proxy');
      const res = await fetchApi.fetch(`${base}/fleetview/voice/say`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) return;
      const pcm = await res.arrayBuffer();
      if (!pcm || pcm.byteLength === 0) return;
      if (!audioCtxRef.current) audioCtxRef.current = new AudioContext();
      const ctx = audioCtxRef.current;
      if (ctx.state === 'suspended') await ctx.resume();
      const f32 = new Float32Array(pcm);
      const buf = ctx.createBuffer(1, f32.length, 24000);
      buf.copyToChannel(f32, 0);
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(ctx.destination);
      src.start();
    } catch { /* narration is best-effort */ }
  }, [fetchApi, discovery]);

  const handleStory = useCallback((sha: string, story: string) => {
    setStorySha(sha);
    setStoryText(story);
    if (narrationOn) speak(story);
  }, [narrationOn, speak]);

  const handleHolmes = useCallback(
    async (journey: Journey, event: JourneyEvent) => {
      const sha = (journey.sha ?? '').slice(0, 7);
      const stage = fullLabel(event.stage);
      const conclusion = (event.detail as Record<string, string>)?.conclusion;
      const q = conclusion
        ? `Why did the ${stage} gate fail for commit ${sha}? Conclusion: ${conclusion}.`
        : `What happened at the ${stage} gate for commit ${sha}?`;
      await askHolmes(q);
    },
    [askHolmes],
  );

  const { connected, lastFrame } = useJourneysStream({
    narrationOn,
    speakFn: narrationOn ? speak : undefined,
    onStory: handleStory,
  });

  return (
    <EstatePage title={TITLE} lead={LEAD}>
      <Section
        title="The river"
        blurb="Every push, every gate, every merge. Refreshes every 30 seconds."
        testId="river-main"
      >
        {/* Controls row */}
        <Box display="flex" alignItems="center" flexWrap="wrap" style={{ gap: 8 }} mb={2}>
          <Button
            size="small"
            variant={narrationOn ? 'contained' : 'outlined'}
            color={narrationOn ? 'primary' : 'default'}
            startIcon={narrationOn ? <VolumeUp /> : <VolumeOff />}
            onClick={() => setNarrationOn(v => !v)}
            data-testid="river-narration-toggle"
          >
            {narrationOn ? 'Narration on' : 'Narration off'}
          </Button>
          {connected && (
            <Typography variant="caption" color="textSecondary">
              Live stream connected
            </Typography>
          )}
          {lastFrame && narrationOn && (
            <Typography
              variant="caption"
              color="textSecondary"
              style={{ fontStyle: 'italic', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              data-testid="river-live-narration"
            >
              {lastFrame.narration}
            </Typography>
          )}
          <Box flex={1} />
          <TimeScrub onChange={setTimeAsOf} currentAsOf={timeAsOf} />
        </Box>

        {/* Holmes interrogation panel */}
        {(holmesAsking || holmesAnswer || holmesError) && (
          <Paper elevation={0} className={classes.holmesPanel} data-testid="river-holmes-panel">
            <Box display="flex" alignItems="center" mb={1}>
              <BugReport style={{ color: '#ff3366', marginRight: 8, fontSize: 18 }} />
              <Typography variant="overline" style={{ color: '#ff3366', flex: 1 }}>
                Ask Holmes
              </Typography>
              {holmesAsking && <CircularProgress size={14} style={{ color: '#ffaa00' }} />}
              <Button size="small" onClick={() => { setStoryText(null); setStorySha(null); }} style={{ fontSize: '0.65rem' }}>
                Dismiss
              </Button>
            </Box>
            {holmesAnswer && (
              <Typography variant="body2" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                {holmesAnswer}
              </Typography>
            )}
            {holmesError && (
              <Typography variant="caption" style={{ color: '#ff6699' }}>
                {holmesError}
              </Typography>
            )}
          </Paper>
        )}

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

            {timeAsOf && (
              <Box mb={2} display="flex" alignItems="center" style={{ gap: 8 }}>
                <InfoOutlined style={{ fontSize: 14, color: '#ffaa00' }} />
                <Typography variant="caption" style={{ color: '#ffaa00' }}>
                  Showing the river as it was at {new Date(timeAsOf).toLocaleString()}.
                  {envelope.as_of ? ` (${envelope.journeys.length} journeys recorded by then)` : ''}
                </Typography>
              </Box>
            )}

            <Typography variant="body2" color="textSecondary" style={{ marginBottom: 16 }}>
              {envelope.journeys.length === 0
                ? 'No journeys recorded yet. Run bin/estate-deploy-recorder to populate the ledger.'
                : `${envelope.journeys.length} commit${envelope.journeys.length === 1 ? '' : 's'} in the ledger.`}
            </Typography>

            {/* Legend */}
            <Box display="flex" flexWrap="wrap" alignItems="center" mb={2}>
              <Typography variant="overline" style={{ marginRight: 8 }}>Gate key:</Typography>
              {([
                { status: 'pass', label: 'Passed' },
                { status: 'fail', label: 'Failed' },
                { status: 'pending', label: 'Pending' },
                { status: 'cancelled', label: 'Cancelled' },
                { status: 'unknown', label: 'Unknown' },
              ] as const).map(({ status, label }) => (
                <Box key={status} display="flex" alignItems="center" style={{ marginRight: 12 }}>
                  <Box
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      borderWidth: 2,
                      borderStyle: status === 'fail' || status === 'cancelled' ? 'dashed' : 'solid',
                      borderColor: STATUS_COLOR[status],
                      background: status === 'pass' ? STATUS_COLOR[status] : 'transparent',
                      marginRight: 4,
                    }}
                  />
                  <Typography variant="caption">{label}</Typography>
                </Box>
              ))}
            </Box>

            <Divider style={{ marginBottom: 16 }} />

            {/* Story mode overlay */}
            {storyText && !holmesAnswer && (
              <Paper
                elevation={2}
                style={{ padding: 16, marginBottom: 16, background: 'rgba(0,204,136,0.08)', border: '1px solid #00cc88' }}
                data-testid="river-story"
              >
                <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                  <Box>
                    <Typography variant="overline" style={{ color: '#00cc88' }}>
                      Story mode — {storySha?.slice(0, 7)}
                    </Typography>
                    <Typography variant="body1" style={{ marginTop: 4, fontStyle: 'italic' }}>
                      {storyText}
                    </Typography>
                  </Box>
                  <Button size="small" onClick={() => setStoryText(null)}>Close</Button>
                </Box>
              </Paper>
            )}

            {envelope.journeys.length === 0 ? (
              <Paper elevation={0} className={classes.emptyPaper}>
                <Typography color="textSecondary" style={{ fontStyle: 'italic' }}>
                  The ledger is empty. No commits have been recorded yet.
                </Typography>
                <Typography variant="caption" color="textSecondary" display="block" style={{ marginTop: 8 }}>
                  Run <code>bin/estate-deploy-recorder</code> to record the first journeys.
                </Typography>
              </Paper>
            ) : (
              envelope.journeys.map(j => (
                <JourneyRow
                  key={j.sha}
                  journey={j}
                  onStory={narrationOn ? handleStory : undefined}
                  onHolmes={handleHolmes}
                />
              ))
            )}
          </>
        )}
      </Section>
    </EstatePage>
  );
}

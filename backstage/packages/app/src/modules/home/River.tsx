// crew#973 CP2+CP3: the Deploy River page (/river).
//
// CP2: The estate's Definition of Done rendered as a river of commits: each commit travels
// through gates (push → auto-PR → fast-gate → crucible → merge → build-multiarch →
// trivy → cosign → flux reflector → image-automation → deploy-when-green → reconcile →
// pod ready → first production log line).
//
// CP3: Narrator hook — SSE tail from the backend, with an ambient narration mode.
// When on, the voice engine speaks each transition as it arrives. Story mode speaks
// a commit's full journey when you focus it. No LLM narrates: templates over the
// ledger, deterministic from real timestamps.
//
// Data: `GET /api/fleetview/journeys` from the fleetview backend, reading
// deploy_journeys / deploy_journey_events written by bin/estate-deploy-recorder.
// SSE stream: `GET /api/fleetview/journeys/stream` tails new events.
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import Box from '@material-ui/core/Box';
import Button from '@material-ui/core/Button';
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

export type JourneyFrame = {
  sha: string;
  state: string;
  last_event: JourneyEvent | null;
  narration: string;
  story: string;
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

// ─── Hook: journeys data ───────────────────────────────────────────────────────

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

// ─── Hook: SSE narration stream ───────────────────────────────────────────────

/**
 * crew#973 CP3: SSE tail for ambient narration.
 *
 * Connects to `GET /api/fleetview/journeys/stream`. Each frame carries a `narration`
 * (one sentence for the newest event) and a `story` (paragraph for the full journey).
 * When `speakFn` is provided, each narration is spoken aloud via the voice engine.
 * `onStory` is called when a person focuses a journey for its story.
 */
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
  // Refs so the SSE callbacks always read the current values without stale closure.
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
      if (!e.data || e.data.startsWith(':')) return; // heartbeat
      try {
        const frame = JSON.parse(e.data) as JourneyFrame;
        if (!frame || !frame.narration) return;
        // Skip if we've already narrated this sha
        if (lastShaRef.current === frame.sha) return;
        lastShaRef.current = frame.sha;
        setLastFrame(frame);
        if (narrationOnRef.current && speakFnRef.current && frame.narration) {
          speakFnRef.current(frame.narration);
        }
        if (onStoryRef.current && frame.story) {
          onStoryRef.current(frame.sha, frame.story);
        }
      } catch {
        // malformed frame
      }
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
      esRef.current = null;
      // Reconnect after 5s using the stable connect reference
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
  // connect is stable: discovery is stable from useApi, and speakFn/narrationOn
  // are read via refs inside connect so this effect never re-runs.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connect]);

  return { connected, lastFrame };
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

function JourneyRow({ journey, onStory }: { journey: Journey; onStory?: (sha: string, story: string) => void }) {
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

  const handleStory = () => {
    if (!onStory) return;
    // Build a basic story from events (story from SSE overrides this when streaming)
    const failCount = journey.events.filter(e => e.status === 'fail').length;
    const state = journey.state;
    const started = journey.started_at ? new Date(journey.started_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : null;
    const merged = journey.merged_at ? new Date(journey.merged_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : null;
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
    onStory(journey.sha, story + '.');
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
        {onStory && (
          <Button size="small" onClick={handleStory} style={{ fontSize: '0.65rem' }}>
            Hear it
          </Button>
        )}
        {journey.title && (
          <Typography
            variant="body2"
            style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              maxWidth: 300,
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
  const fetchApi = useApi(fetchApiRef);
  const discovery = useApi(discoveryApiRef);
  const { envelope, loading } = useJourneys();
  const [narrationOn, setNarrationOn] = useState(false);
  const [storyText, setStoryText] = useState<string | null>(null);
  const [storySha, setStorySha] = useState<string | null>(null);
  // Lazy AudioContext: created on first narration, reused across utterances.
  const audioCtxRef = useRef<AudioContext | null>(null);

  // Speak one sentence via the board's /voice/say HTTP endpoint + WebAudio.
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
      // Lazily create / reuse the AudioContext (same pattern as useEstateVoice).
      if (!audioCtxRef.current) {
        audioCtxRef.current = new AudioContext();
      }
      const ctx = audioCtxRef.current;
      if (ctx.state === 'suspended') await ctx.resume();
      const f32 = new Float32Array(pcm);
      const buf = ctx.createBuffer(1, f32.length, 24000);
      buf.copyToChannel(f32, 0);
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(ctx.destination);
      src.start();
    } catch {
      // narration is best-effort; a failure must not crash the stream
    }
  }, [fetchApi, discovery]);

  const handleStory = useCallback((sha: string, story: string) => {
    setStorySha(sha);
    setStoryText(story);
    if (narrationOn) speak(story);
  }, [narrationOn, speak]);

  const { connected, lastFrame } = useJourneysStream({
    narrationOn,
    speakFn: narrationOn ? speak : undefined,
    onStory: handleStory,
  });

  return (
    <EstatePage title={TITLE} lead={LEAD}>
      <Section title="The river" blurb="Every push, every gate, every merge. Refreshes every 30 seconds." testId="river-main">
        {/* Narration controls */}
        <Box display="flex" alignItems="center" mb={2} style={{ gap: 8 }}>
          <Button
            size="small"
            variant={narrationOn ? 'contained' : 'outlined'}
            color={narrationOn ? 'primary' : 'default'}
            onClick={() => setNarrationOn(v => !v)}
            data-testid="river-narration-toggle"
          >
            {narrationOn ? '🔊 Narration on' : '🔇 Narration off'}
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
              style={{ fontStyle: 'italic', maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              data-testid="river-live-narration"
            >
              {lastFrame.narration}
            </Typography>
          )}
        </Box>

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

            {/* Story mode overlay */}
            {storyText && (
              <Paper elevation={2} style={{ padding: 16, marginBottom: 16, background: 'rgba(0,204,136,0.08)', border: '1px solid #00cc88' }} data-testid="river-story">
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
                <JourneyRow
                  key={j.sha}
                  journey={j}
                  onStory={narrationOn ? handleStory : undefined}
                />
              ))
            )}
          </>
        )}
      </Section>
    </EstatePage>
  );
}

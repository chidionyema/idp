/**
 * /face: the estate's face, full screen, phone first. One page for every surface that talks to the
 * founder -- Fleet links here, Otto and Concierge send this link -- so there is one face, not three
 * (AGENTS.md section 6). Tap to talk; the estate hears, answers and speaks through the face.
 *
 * CHROME-FREE BY LAYER, NOT BY REQUEST (crew#1017: "nav sidebar still docked, not chrome-free").
 * `noHeader` on the page blueprint removes the page header, not the app's docked sidebar; this
 * component rendered inside the layout pane, 224px to the right of the sidebar, on every laptop.
 * A `position: fixed; inset: 0` layer at a z-index above every drawer and app bar paints over ALL
 * app chrome deterministically -- no dependency on Backstage's layout class names, which change
 * between versions, and nothing to keep in sync. The page IS the screen.
 *
 * THE AVATAR IS NEVER CROPPED BY THE CONTROLS (crew#1017: "'Tap to talk' cuts off avatar bottom").
 * The old layout was `grid-template-rows: 1fr auto`: the control block consumed viewport height
 * and the avatar's chest was cropped at the canvas bottom edge -- the 'upper' camera view ends
 * mid-torso wherever the canvas ends. The face now owns the whole viewport and the controls float
 * over it as a glass pill near the bottom, so the model is framed once by the camera, never by the
 * button.
 */
import { useEffect, useState, type CSSProperties } from 'react';
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import EstateFace from './EstateFace';
import FleetBackdrop from './FleetBackdrop';
import { useResearch } from './useResearch';
import { useEstateVoice } from './useEstateVoice';
import { useVoiceRouter } from './useVoiceRouter';
import { useFaceVoiceEngine } from './faceVoiceEngine';
import { useEstateStrip } from './EstateStrip';
import { useMilestones } from './useMilestones';
import { useAgentJobs, type LoadedJobs } from './useAgentJobs';
import { clampLevel, getLevel, setLevel, subscribeLevel } from './faceAudio';
import {
  ageLabel,
  CLAIM_STALE_MS,
  ESTATE_STALE_MS,
  freshness,
} from './faceFreshness';

// One clock for every age on the page, re-read each 30s so "4 min ago" does not freeze at the
// moment the data arrived (a frozen age is its own kind of stale).
function useNow(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(t);
  }, []);
  return now;
}

// The volume the face speaks at, as a live number (faceAudio.ts holds it and remembers it).
function useFaceLevel(): number {
  const [level, set] = useState(getLevel());
  useEffect(() => subscribeLevel(() => set(getLevel())), []);
  return level;
}

/** "Voice: <name> (engine)" -- which voice is actually speaking, so a switch is visible. */
export function activeVoiceLabel(current: { engine: string; voice: string }): string {
  return current.engine === 'voice-router'
    ? `Voice: ${current.voice}`
    : `Voice: ${current.voice} · ${current.engine}`;
}

// THE FACE'S VOICE PATH, BEHIND A FLAG (2026-10-16). The face now speaks through useVoiceRouter
// -- the streaming socket (partials while you speak, first audio median 2.26s against the old
// path's 3.0-3.8s, and the lip-synced mouth, which the old path's /voice/say loop had and this
// one never did). `estate.face.voice = legacy` in localStorage puts the old useEstateVoice loop
// back without a deploy, until the old path is deleted outright. Both hooks mount (their rules
// of hooks must not branch); only the chosen one's handlers are wired to the page. The flag is
// read per render, not at module load, so a test can set it before rendering -- for a person it
// cannot change between renders without a reload, which is exactly the semantics it needs.
function faceVoicePrefersLegacy(): boolean {
  try {
    return window.localStorage.getItem('estate.face.voice') === 'legacy';
  } catch {
    return false;
  }
}

const LABEL: Record<string, string> = {
  off: 'Tap to talk',
  listening: 'Listening…',
  thinking: 'Thinking…',
  speaking: 'Speaking…',
  error: 'Tap to try again',
};

export function FaceFindingsStrip() {
  const loaded = useResearch(1);
  if (loaded.state !== 'ready' || loaded.claims.length === 0) return null;
  const claim = loaded.claims[0];
  const now = useNow();
  const age = ageLabel(claim.created_at, now);
  const stale = freshness(claim.created_at, now, CLAIM_STALE_MS) === 'stale';
  const line =
    claim.statement.length > 140
      ? `${claim.statement.slice(0, 139)}…`
      : claim.statement;
  return (
    <div
      data-testid="face-research-strip"
      style={{
        position: 'absolute',
        top: 'calc(env(safe-area-inset-top, 0px) + 44px)',
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(680px, calc(100% - 32px))',
        textAlign: 'center',
        fontSize: 12,
        lineHeight: 1.5,
        color: 'rgba(232,237,245,0.55)',
        textShadow: '0 1px 8px rgba(11,14,20,0.8)',
        pointerEvents: 'none',
      }}
    >
      {line}
      {/* How old the finding is. A claim with no usable date says so rather than going unlabelled. */}
      <span data-testid="face-research-age" data-freshness={freshness(claim.created_at, now, CLAIM_STALE_MS)} style={{ opacity: 0.7, color: stale ? '#e8b86d' : undefined }}>
        {' '}· {age ?? 'age unknown'}
      </span>
    </div>
  );
}

export function FaceEstateLine() {
  // The estate's vitals under the wordmark: green lane and router burn, one muted line, the
  // findings strip's own design law (silent while loading or unreadable -- the face is not a
  // dashboard). Research already owns the line below; this line is the lane and the burn, from
  // the SAME /estate envelope /fleet reads, so the two surfaces can never disagree.
  const loaded = useEstateStrip();
  const now = useNow();
  if (loaded.state !== 'ready') return null;
  const { green, burn } = loaded.body;
  const asOf = loaded.body.generated_at;
  const estateStale = freshness(asOf, now, ESTATE_STALE_MS);
  const bits: string[] = [];
  if (green?.available) {
    const lanes = green.state?.lanes ?? {};
    const red = Object.values(lanes).filter(
      l => (l?.status ?? '') !== 'green',
    ).length;
    // Three states, exactly as the strip draws them: unknown is not red. Collapsing undefined
    // into 'main RED' would have the face cry wolf during every lane-reader hiccup.
    if (green.main?.green === undefined) {
      bits.push('main unknown');
    } else if (
      green.main.green &&
      red === 0 &&
      (green.work_lost?.length ?? 0) === 0
    ) {
      bits.push('main green · all lanes green');
    } else {
      bits.push(green.main.green ? `${red} red lane(s)` : 'main RED');
    }
  }
  if (burn?.measured) bits.push(`$${(burn.total_usd ?? 0).toFixed(2)} burn`);
  if (bits.length === 0) return null;
  bits.push(
    estateStale === 'stale'
      ? `STALE: as of ${ageLabel(asOf, now)}`
      : `as of ${ageLabel(asOf, now) ?? 'an unknown time'}`,
  );
  return (
    <div
      data-testid="face-estate-line"
      style={{
        position: 'absolute',
        top: 'calc(env(safe-area-inset-top, 0px) + 68px)',
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(680px, calc(100% - 32px))',
        textAlign: 'center',
        fontSize: 11,
        lineHeight: 1.5,
        letterSpacing: '0.04em',
        color: 'rgba(232,237,245,0.45)',
        textShadow: '0 1px 8px rgba(11,14,20,0.8)',
        pointerEvents: 'none',
      }}
    >
      {bits.join(' · ')}
    </div>
  );
}

const clamp = (lines: number): CSSProperties => ({
  display: '-webkit-box',
  WebkitLineClamp: lines,
  WebkitBoxOrient: 'vertical',
  overflow: 'hidden',
});

// THE AGENTS THE FACE SENT (voice: "give an agent a job ..."). Up to three of the newest jobs, one
// line each: running ones first so a launched job is visible the moment it exists. Silent while
// loading and while nothing has run; an unreadable board says so rather than showing an empty one.
export function FaceAgentJobs({ loaded }: { loaded: LoadedJobs }) {
  if (loaded.state === 'loading') return null;
  const box: CSSProperties = {
    position: 'absolute',
    top: 'calc(env(safe-area-inset-top, 0px) + 92px)',
    left: '50%',
    transform: 'translateX(-50%)',
    width: 'min(680px, calc(100% - 32px))',
    display: 'grid',
    gap: 4,
    textAlign: 'center',
    fontSize: 12,
    lineHeight: 1.4,
    color: 'rgba(232,237,245,0.7)',
    textShadow: '0 1px 8px rgba(11,14,20,0.8)',
    pointerEvents: 'none',
  };
  if (loaded.state === 'unavailable') {
    return (
      <div data-testid="face-agent-jobs" data-state="unavailable" style={box}>
        <span style={{ opacity: 0.55 }}>Agent jobs unavailable: {loaded.error}</span>
      </div>
    );
  }
  const jobs = [...loaded.jobs]
    .sort((a, b) => Number(b.state === 'running') - Number(a.state === 'running'))
    .slice(0, 3);
  if (jobs.length === 0) return null;
  const mark = { running: '●', done: '✓', failed: '✕' } as const;
  return (
    <div data-testid="face-agent-jobs" data-state="ready" style={box}>
      {jobs.map((j) => (
        <div key={j.run_id} style={{ ...clamp(1), opacity: j.state === 'running' ? 1 : 0.6 }}>
          {mark[j.state]} {j.task} — {j.state === 'running' ? j.stage : j.state}
          {j.state === 'failed' && j.reason ? `: ${j.reason}` : ''}
        </div>
      ))}
    </div>
  );
}

export function FacePage() {
  const legacy = useEstateVoice();
  const router = useVoiceRouter();
  // Production has no voice router behind /voice/*; a router that probes unreachable hands the
  // face to the legacy engine (faceVoiceEngine.ts) instead of leaving a dead button.
  const engine = useFaceVoiceEngine(faceVoicePrefersLegacy(), router);
  const chosen = engine === 'legacy' ? legacy : router;
  const voice = {
    ...chosen,
    // Only the router hook streams partials; reading it off the union's common shape keeps the
    // page one type.
    partial: (chosen as { partial?: string }).partial,
  };
  // Milestones spoken through the SAME voice engine as everything else (idp#5737 item 3). The
  // gate lives in milestoneSpeech.ts; this only joins the news stream to the mouth. Off by
  // default: the face does not start narrating unasked.
  const milestones = useMilestones(voice.speak);
  // The agents launched by voice, followed to their end and announced through the same mouth.
  const agentJobs = useAgentJobs(voice.speak);
  const level = useFaceLevel();
  // Voices a person can pick are the chosen engine's own catalogue, flattened to engine/voice
  // pairs. voice-router has exactly one voice, so its list is one entry and the picker says so
  // instead of offering a choice that does nothing.
  const voiceOptions = Object.entries(voice.catalogue ?? {}).flatMap(
    ([eng, names]) => (names as string[]).map(n => ({ engine: eng, voice: n })),
  );
  const [pickNote, setPickNote] = useState('');
  // A FAILED MICROPHONE MUST BE RE-ASKABLE -- and the tap must not depend on a state comparison
  // that has to be kept in step with the label below.
  //
  // The rule here was `on = state !== 'off' && state !== 'error'`, with the handler
  // `on ? stop() : start()`. That happens to re-ask in 'error', but it gets there by two
  // negations that must stay inverted against the label map: add a state, and the button
  // silently changes meaning. The label directly below already promises the behaviour --
  // `error: 'Tap to try again'` -- so the tap is expressed as the same fact: stop a live
  // microphone, start anything else. 'error' is not running, so it can only mean "ask again".
  // Matching FleetReactorApp.openVoice, which was fixed for the founder's phone on 2026-10-05
  // ("it says tap the mic to try again, and when you tap nothing happens" -- the tap WAS
  // firing, as a stop, on a microphone that had already failed).
  const live =
    voice.state === 'listening' ||
    voice.state === 'thinking' ||
    voice.state === 'speaking';
  const on = live;
  // The wordmark is the estate's own name (LAW 46), not a string in this file. On a chrome-free
  // page nothing else names the product, so it reads here, crisp on near-black -- the fix for
  // "Bytesync title washed out", which was the sidebar's faded wordmark doing the naming before.
  const title = useApi(configApiRef).getOptionalString('app.title') ?? 'Estate';
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 2000,
        background:
          'radial-gradient(ellipse at 50% 30%, #1d2533 0%, #0b0e14 70%)',
        color: '#e8edf5',
        overflow: 'hidden',
      }}
    >
      <FleetBackdrop />

      {/* THE FINDINGS STRIP (idp#5714): the research department's newest verified claim, one
          muted line under the wordmark. Silent while loading or unreadable -- the face is not a
          dashboard, and the voice loop already reports failures -- but whenever the department
          has produced a finding, the estate's face carries it. Never interactive: taps pass
          through to the face. */}
      <FaceFindingsStrip />
      <FaceEstateLine />
      <FaceAgentJobs loaded={agentJobs} />

      {/* The face owns the whole viewport; everything else floats over it. */}
      <EstateFace height="100%" />

      {/* THE WORDMARK, top centre under the status line. */}
      <div
        style={{
          position: 'absolute',
          top: 'calc(env(safe-area-inset-top, 0px) + 16px)',
          width: '100%',
          textAlign: 'center',
          fontSize: 13,
          fontWeight: 700,
          letterSpacing: '0.28em',
          textTransform: 'uppercase',
          color: 'rgba(232,237,245,0.92)',
          textShadow: '0 1px 8px rgba(11,14,20,0.8)',
          pointerEvents: 'none',
        }}
      >
        {title}
      </div>

      {/* THE CONTROLS, one glass pill floating over the avatar's lower edge. `pointerEvents:
          'none'` on the pill lets gaze/mouse through to the face everywhere except the button. */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          transform: 'translateX(-50%)',
          bottom: 'calc(env(safe-area-inset-bottom, 0px) + 16px)',
          width: 'min(480px, calc(100% - 32px))',
          display: 'grid',
          gap: 10,
          padding: '14px 16px',
          textAlign: 'center',
          background: 'rgba(11,14,20,0.55)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          border: '1px solid rgba(232,237,245,0.14)',
          borderRadius: 22,
          pointerEvents: 'none',
        }}
      >
        {/* CAPTIONS ARE BOUND, NOT UNBOUNDED (2026-10-16, "caption text covers the face"): a long
            answer used to grow this pill upward over the avatar's chest and mouth. The words are
            capped where the pill is wide, and the full text lives in the DOM for screen readers. */}
        {(voice.partial || voice.heard) && (
          <div style={{ ...clamp(1), opacity: 0.65, fontSize: 14 }}>
            You: {voice.partial || voice.heard}
          </div>
        )}
        {voice.reply && (
          <div style={{ ...clamp(3), fontSize: 17, lineHeight: 1.45 }}>{voice.reply}</div>
        )}
        {voice.detail && (
          <div style={{ opacity: 0.55, fontSize: 12 }}>{voice.detail}</div>
        )}
        {/* ONE TAP, NOT A SETTINGS TOUR (2026-10-08). Set only when the mic was refused inside a
            home-screen icon, where iOS does not persist a grant and "tap again" replays the same
            refusal forever (useEstateVoice.ts: isStandaloneHomeScreen). `target="_blank"` from a
            standalone shell is handed to Safari as a real tab -- the one place this refusal
            actually clears -- so this is a working escape, not an instruction to go find a toggle. */}
        {voice.micRecoveryUrl && (
          <a
            href={voice.micRecoveryUrl}
            target="_blank"
            rel="noopener"
            style={{
              pointerEvents: 'auto',
              fontSize: 13,
              fontWeight: 600,
              color: '#7fd1b9',
              textDecoration: 'underline',
            }}
          >
            Open in Safari to use the mic
          </a>
        )}
        {/* WHICH VOICE IS SPEAKING, AND LOUD ENOUGH TO HEAR (idp#6784). The label names the live
            voice so a switch is visible; the slider is the level faceAudio.ts applies to every
            clause, remembered on this device. */}
        <div
          data-testid="face-voice-active"
          style={{ fontSize: 12, opacity: 0.8, pointerEvents: 'none' }}
        >
          {activeVoiceLabel(voice.current)}
          {voice.state === 'speaking' ? ' · speaking' : ''}
        </div>
        <label
          style={{
            pointerEvents: 'auto',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            justifyContent: 'center',
            fontSize: 12,
          }}
        >
          Volume
          <input
            type="range"
            data-testid="face-volume"
            aria-label="Voice volume"
            min={0}
            max={100}
            value={Math.round(level * 100)}
            onChange={e => setLevel(clampLevel(Number(e.target.value) / 100))}
            style={{ width: 160 }}
          />
          <span style={{ width: 34, textAlign: 'right' }}>
            {Math.round(level * 100)}%
          </span>
        </label>
        {voiceOptions.length > 1 && (
          <select
            data-testid="face-voice-picker"
            aria-label="Choose voice"
            value={`${voice.current.engine}/${voice.current.voice}`}
            onChange={async e => {
              const [eng, ...rest] = e.target.value.split('/');
              setPickNote(await voice.selectVoice(eng, rest.join('/')));
            }}
            style={{
              pointerEvents: 'auto',
              justifySelf: 'center',
              background: 'rgba(11,14,20,0.7)',
              color: '#e8edf5',
              border: '1px solid rgba(232,237,245,0.25)',
              borderRadius: 8,
              padding: '4px 8px',
              fontSize: 12,
            }}
          >
            {voiceOptions.map(o => (
              <option key={`${o.engine}/${o.voice}`} value={`${o.engine}/${o.voice}`}>
                {o.voice} ({o.engine})
              </option>
            ))}
          </select>
        )}
        {pickNote && <div style={{ fontSize: 11, opacity: 0.6 }}>{pickNote}</div>}
        {/* THE MILESTONE TOGGLE (idp#5737 item 3): the explicit switch the item asks for. It sits
            in the same pill as the mic so "does the face talk on its own?" is answerable in one
            glance, and it is a real control -- quiet hours and the rate cap are the gate's job, not
            this button's. */}
        <button
          type="button"
          data-testid="face-milestone-toggle"
          aria-pressed={milestones.prefs.enabled}
          onClick={() => milestones.setEnabled(!milestones.prefs.enabled)}
          style={{
            pointerEvents: 'auto',
            justifySelf: 'center',
            background: 'none',
            border: 'none',
            padding: '2px 6px',
            fontSize: 12,
            letterSpacing: '0.04em',
            cursor: 'pointer',
            color: milestones.prefs.enabled
              ? '#7fd1b9'
              : 'rgba(232,237,245,0.55)',
          }}
        >
          {milestones.prefs.enabled
            ? 'Milestones: spoken'
            : 'Milestones: silent'}
        </button>
        <button
          type="button"
          data-testid="face-mic"
          onClick={() => (live ? voice.stop() : voice.start())}
          disabled={!voice.available}
          style={{
            pointerEvents: 'auto',
            justifySelf: 'center',
            minWidth: 200,
            padding: '16px 28px',
            borderRadius: 999,
            border: 'none',
            fontSize: 17,
            fontWeight: 600,
            color: '#0b0e14',
            background: on ? '#7fd1b9' : '#e8edf5',
            cursor: voice.available ? 'pointer' : 'not-allowed',
            boxShadow: '0 4px 24px rgba(0,0,0,0.35)',
          }}
        >
          {voice.available
            ? on
              ? `${LABEL[voice.state]} · tap to stop`
              : LABEL[voice.state]
            : voice.checking
              ? 'Connecting…'
              : 'Voice is not available here'}
        </button>
      </div>
    </div>
  );
}

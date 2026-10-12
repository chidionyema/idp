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
import { configApiRef, useApi } from '@backstage/frontend-plugin-api';
import EstateFace from './EstateFace';
import FleetBackdrop from './FleetBackdrop';
import { useResearch } from './useResearch';
import { useEstateVoice } from './useEstateVoice';
import { useEstateStrip } from './EstateStrip';
import { useMilestones } from './useMilestones';

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
    </div>
  );
}

export function FaceEstateLine() {
  // The estate's vitals under the wordmark: green lane and router burn, one muted line, the
  // findings strip's own design law (silent while loading or unreadable -- the face is not a
  // dashboard). Research already owns the line below; this line is the lane and the burn, from
  // the SAME /estate envelope /fleet reads, so the two surfaces can never disagree.
  const loaded = useEstateStrip();
  if (loaded.state !== 'ready') return null;
  const { green, burn } = loaded.body;
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

export function FacePage() {
  const voice = useEstateVoice();
  // Milestones spoken through the SAME voice engine as everything else (idp#5737 item 3). The
  // gate lives in milestoneSpeech.ts; this only joins the news stream to the mouth. Off by
  // default: the face does not start narrating unasked.
  const milestones = useMilestones(voice.speak);
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
        {voice.heard && (
          <div style={{ opacity: 0.65, fontSize: 14 }}>You: {voice.heard}</div>
        )}
        {voice.reply && (
          <div style={{ fontSize: 17, lineHeight: 1.45 }}>{voice.reply}</div>
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
            : 'Voice is not available here'}
        </button>
      </div>
    </div>
  );
}

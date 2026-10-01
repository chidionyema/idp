/**
 * /face: the estate's face, full screen, phone first. One page for every surface that talks to the
 * founder -- Fleet links here, Otto and Concierge send this link -- so there is one face, not three
 * (AGENTS.md section 6). Tap to talk; the estate hears, answers and speaks through the face.
 */
import EstateFace from './EstateFace';
import FleetBackdrop from './FleetBackdrop';
import { useEstateVoice } from './useEstateVoice';

const LABEL: Record<string, string> = {
  off: 'Tap to talk',
  listening: 'Listening…',
  thinking: 'Thinking…',
  speaking: 'Speaking…',
  error: 'Tap to try again',
};

export function FacePage() {
  const voice = useEstateVoice();
  const on = voice.state !== 'off' && voice.state !== 'error';
  return (
    <div
      style={{
        height: '100dvh',
        display: 'grid',
        gridTemplateRows: '1fr auto',
        background: 'radial-gradient(ellipse at 50% 30%, #1d2533 0%, #0b0e14 70%)',
        color: '#e8edf5',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <FleetBackdrop />
      <div style={{ position: 'relative', minHeight: 0 }}>
        <EstateFace height="100%" />
      </div>
      <div
        style={{
          position: 'relative',
          display: 'grid',
          gap: 12,
          padding: '12px 16px 20px',
          textAlign: 'center',
        }}
      >
        {voice.heard && <div style={{ opacity: 0.6, fontSize: 14 }}>You: {voice.heard}</div>}
        {voice.reply && <div style={{ fontSize: 17, lineHeight: 1.45 }}>{voice.reply}</div>}
        {voice.detail && <div style={{ opacity: 0.5, fontSize: 12 }}>{voice.detail}</div>}
        <button
          type="button"
          onClick={() => (on ? voice.stop() : voice.start())}
          disabled={!voice.available}
          style={{
            justifySelf: 'center',
            minWidth: 200,
            padding: '16px 28px',
            borderRadius: 999,
            border: 'none',
            fontSize: 17,
            fontWeight: 600,
            color: '#0b0e14',
            background: on ? '#7fd1b9' : '#e8edf5',
          }}
        >
          {voice.available ? (on ? `${LABEL[voice.state]} · tap to stop` : LABEL[voice.state]) : 'Voice is not available here'}
        </button>
      </div>
    </div>
  );
}

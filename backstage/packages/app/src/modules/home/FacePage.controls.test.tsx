/**
 * THE FACE'S NEW CONTROLS (idp#6784): a volume you can set, a voice you can name and change, and
 * news that says how old it is. The hooks are mocked (as in FacePage.micRetry.test.tsx); what is
 * under test is the page wiring, not the browser's audio.
 */
// `jest` is the global on purpose -- see FacePage.micRetry.test.tsx for why.
import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FacePage } from './FacePage';
import { getLevel, resetLevelForTest, VOLUME_KEY } from './faceAudio';

beforeEach(() => {
  window.localStorage.setItem('estate.face.voice', 'legacy');
  window.localStorage.removeItem(VOLUME_KEY);
  resetLevelForTest();
});

jest.mock('./useEstateVoice', () => ({ useEstateVoice: jest.fn() }));
jest.mock('@backstage/frontend-plugin-api', () => ({
  configApiRef: { id: 'core.config' },
  useApi: () => ({ getOptionalString: () => 'Estate' }),
}));
jest.mock('./EstateFace', () => ({ __esModule: true, default: () => null }));
jest.mock('./FleetBackdrop', () => ({ __esModule: true, default: () => null }));
// A claim three days old: past the 24 h window, so the strip must call it stale-aged, not fresh.
jest.mock('./useResearch', () => ({
  useResearch: () => ({
    state: 'ready',
    claims: [
      {
        created_at: new Date(Date.now() - 3 * 24 * 3600 * 1000).toISOString(),
        status: 'verified',
        statement: 'the router held under load',
      },
    ],
  }),
}));

const mocked = require('./useEstateVoice').useEstateVoice as jest.Mock;

function voice(over: Record<string, unknown> = {}) {
  return {
    state: 'off',
    detail: '',
    heard: '',
    reply: '',
    available: true,
    start: jest.fn(),
    stop: jest.fn(),
    speak: jest.fn(),
    current: { engine: 'cloud', voice: 'hannah' },
    catalogue: { cloud: ['hannah', 'marcus'], say: [], kokoro: ['af_heart'], piper: [] },
    selectVoice: jest.fn(async (_engine: string, _voice: string) => 'now speaking with marcus'),
    ...over,
  };
}

describe('FacePage controls', () => {
  afterEach(() => {
    cleanup();
    jest.clearAllMocks();
  });

  it('names the live voice, and says when it is speaking', () => {
    mocked.mockReturnValue(voice({ state: 'speaking' }));
    render(<FacePage />);
    expect(screen.getByTestId('face-voice-active')).toHaveTextContent(
      'Voice: hannah · cloud · speaking',
    );
  });

  it('the volume slider sets the level faceAudio applies, and remembers it on the device', () => {
    mocked.mockReturnValue(voice());
    render(<FacePage />);
    const slider = screen.getByTestId('face-volume') as HTMLInputElement;
    expect(slider.value).toBe('85');
    fireEvent.change(slider, { target: { value: '40' } });
    expect(getLevel()).toBeCloseTo(0.4, 5);
    expect(window.localStorage.getItem(VOLUME_KEY)).toBe('0.4');
    expect(slider.value).toBe('40');
  });

  it('lists every catalogue voice and switches through selectVoice', async () => {
    const v = voice();
    mocked.mockReturnValue(v);
    render(<FacePage />);
    const picker = screen.getByTestId('face-voice-picker') as HTMLSelectElement;
    expect(Array.from(picker.options).map(o => o.value)).toEqual([
      'cloud/hannah',
      'cloud/marcus',
      'kokoro/af_heart',
    ]);
    fireEvent.change(picker, { target: { value: 'cloud/marcus' } });
    await waitFor(() => expect(v.selectVoice).toHaveBeenCalledWith('cloud', 'marcus'));
    expect(await screen.findByText('now speaking with marcus')).toBeInTheDocument();
  });

  it('offers no picker when there is only one voice to pick', () => {
    mocked.mockReturnValue(
      voice({ catalogue: { cloud: ['hannah'], say: [], kokoro: [], piper: [] } }),
    );
    render(<FacePage />);
    expect(screen.queryByTestId('face-voice-picker')).toBeNull();
  });

  it('puts an age on the finding, and marks an old one as stale-aged', () => {
    mocked.mockReturnValue(voice());
    render(<FacePage />);
    const age = screen.getByTestId('face-research-age');
    expect(age).toHaveTextContent('3 d ago');
    expect(age).toHaveAttribute('data-freshness', 'stale');
  });
});

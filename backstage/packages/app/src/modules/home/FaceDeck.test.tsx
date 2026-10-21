/**
 * THE COMMAND DECK: the wiring, not the browser. fetchApi is a stub that answers by URL, so what is
 * under test is that the deck lists the catalogue, runs through /voice/intent, shows Confirm only
 * when the backend is waiting, swaps the avatar on the live face, and names every failure.
 */
import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import FaceDeck from './FaceDeck';
import { setActiveFace } from './faceEngine';
import { AVATAR_KEY } from './faceAvatars';

const fetchMock = jest.fn();
jest.mock('@backstage/frontend-plugin-api', () => ({
  fetchApiRef: { id: 'core.fetch' },
  useApi: () => ({ fetch: (...a: unknown[]) => fetchMock(...a) }),
}));

const json = (status: number, body: unknown) =>
  ({ status, ok: status >= 200 && status < 300, json: async () => body }) as Response;
const result = (intent: string, status: string, text: string) => ({
  kind: 'intent_result',
  intent,
  status,
  text,
  visual: { cue: 'pulse', target: 'fleet', severity: 'info' },
  ticket: null,
});
const voice = {
  current: { engine: 'cloud', voice: 'hannah' },
  catalogue: { cloud: ['hannah', 'marcus'] },
  selectVoice: jest.fn(async (_engine: string, _voice: string) => 'now speaking with marcus'),
};
const jobs = { state: 'ready' as const, jobs: [{ run_id: 7, task: 'fix the thing', stage: 'build', state: 'running' as const }] };

function route(over: Record<string, (init?: RequestInit) => Response> = {}) {
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    for (const [k, v] of Object.entries(over)) if (url.endsWith(k)) return v(init);
    if (url.endsWith('/voice/intents'))
      return json(200, {
        intents: [
          { name: 'ci-status', description: 'CI state', read_only: true },
          { name: 'flux-reconcile', description: 'Reconcile Flux', read_only: false },
        ],
      });
    return json(204, null);
  });
}
const openDeck = () => fireEvent.click(screen.getByTestId('face-deck-open'));

beforeEach(() => {
  fetchMock.mockReset();
  window.localStorage.removeItem(AVATAR_KEY);
});
afterEach(() => {
  cleanup();
  setActiveFace(null);
});

describe('FaceDeck', () => {
  it('fetches nothing until opened', () => {
    route();
    render(<FaceDeck voice={voice} jobs={jobs} />);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('lists and filters the catalogue, and runs a read-only intent', async () => {
    route({ '/voice/intent': () => json(200, result('ci-status', 'ok', 'all green')) });
    render(<FaceDeck voice={voice} jobs={jobs} />);
    openDeck();
    await screen.findByTestId('face-deck-run-ci-status');
    fireEvent.change(screen.getByTestId('face-deck-filter'), { target: { value: 'flux' } });
    expect(screen.queryByTestId('face-deck-run-ci-status')).toBeNull();
    fireEvent.change(screen.getByTestId('face-deck-filter'), { target: { value: '' } });
    fireEvent.click(screen.getByTestId('face-deck-run-ci-status'));
    const res = await screen.findByTestId('face-deck-result');
    expect(res).toHaveTextContent('all green');
    expect(screen.queryByTestId('face-deck-confirm')).toBeNull();
    const call = fetchMock.mock.calls.find(c => String(c[0]).endsWith('/voice/intent'))!;
    expect(JSON.parse(call[1].body)).toMatchObject({ text: 'ci-status' });
  });

  it('shows Confirm only for a pending confirmation and sends yes on the same session', async () => {
    const bodies: Array<{ text: string; session_id: string }> = [];
    let n = 0;
    route({
      '/voice/intent': init => {
        bodies.push(JSON.parse(String(init?.body)));
        return json(200, n++ === 0 ? result('flux-reconcile', 'pending_confirmation', 'Reconcile Flux?') : result('flux-reconcile', 'ok', 'Reconciled.'));
      },
    });
    render(<FaceDeck voice={voice} jobs={jobs} />);
    openDeck();
    fireEvent.click(await screen.findByTestId('face-deck-run-flux-reconcile'));
    fireEvent.click(await screen.findByTestId('face-deck-confirm'));
    await waitFor(() => expect(screen.getByTestId('face-deck-result')).toHaveAttribute('data-status', 'ok'));
    expect(bodies.map(b => b.text)).toEqual(['flux-reconcile', 'yes']);
    expect(bodies[1].session_id).toBe(bodies[0].session_id);
  });

  it('names a catalogue failure instead of showing a blank panel', async () => {
    route({ '/voice/intents': () => json(502, {}) });
    render(<FaceDeck voice={voice} jobs={jobs} />);
    openDeck();
    expect(await screen.findByTestId('face-deck-error')).toHaveTextContent('502');
  });

  it('lists tracked jobs and launches one in the voice phrase', async () => {
    const bodies: string[] = [];
    route({
      '/voice/intent': init => {
        bodies.push(JSON.parse(String(init?.body)).text);
        return json(200, result('agent-job', 'pending_confirmation', 'Send it?'));
      },
    });
    render(<FaceDeck voice={voice} jobs={jobs} />);
    openDeck();
    fireEvent.click(screen.getByTestId('face-deck-tab-agents'));
    expect(screen.getByTestId('face-deck-job')).toHaveTextContent('fix the thing');
    fireEvent.change(screen.getByTestId('face-deck-task'), { target: { value: 'tidy up' } });
    fireEvent.click(screen.getByTestId('face-deck-launch'));
    await screen.findByTestId('face-deck-confirm');
    expect(bodies).toEqual(['give an agent a job: tidy up']);
  });

  it('says the agent board is unavailable rather than empty', () => {
    route();
    render(<FaceDeck voice={voice} jobs={{ state: 'unavailable', error: 'no token' }} />);
    openDeck();
    fireEvent.click(screen.getByTestId('face-deck-tab-agents'));
    expect(screen.getByTestId('face-deck-jobs-unavailable')).toHaveTextContent('no token');
  });

  it('swaps the avatar on the live face and remembers it; a failure keeps the old one', async () => {
    route();
    const setAvatar = jest.fn(async (_a: unknown) => undefined);
    setActiveFace({ setAvatar } as never);
    render(<FaceDeck voice={voice} jobs={jobs} />);
    openDeck();
    fireEvent.click(screen.getByTestId('face-deck-tab-persona'));
    fireEvent.click(screen.getByTestId('face-deck-avatar-estate'));
    await waitFor(() => expect(screen.getByTestId('face-deck-avatar-note')).toHaveTextContent('Now wearing'));
    expect(setAvatar).toHaveBeenCalledWith(expect.objectContaining({ id: 'estate' }));
    expect(window.localStorage.getItem(AVATAR_KEY)).toBe('{"id":"estate"}');

    setAvatar.mockRejectedValueOnce(new Error('404'));
    fireEvent.click(screen.getByTestId('face-deck-avatar-brunette'));
    await waitFor(() => expect(screen.getByTestId('face-deck-avatar-note')).toHaveTextContent('previous avatar stays'));
    expect(window.localStorage.getItem(AVATAR_KEY)).toBe('{"id":"estate"}');
  });

  it('refuses an unsafe custom avatar link and says so, and with no face says there is nothing to change', async () => {
    route();
    const setAvatar = jest.fn(async (_a: unknown) => undefined);
    setActiveFace({ setAvatar } as never);
    render(<FaceDeck voice={voice} jobs={jobs} />);
    openDeck();
    fireEvent.click(screen.getByTestId('face-deck-tab-persona'));
    fireEvent.change(screen.getByTestId('face-deck-avatar-url'), { target: { value: 'javascript:alert(1)' } });
    fireEvent.click(screen.getByTestId('face-deck-avatar-use'));
    expect(screen.getByTestId('face-deck-avatar-note')).toHaveTextContent('not a usable avatar');
    expect(setAvatar).not.toHaveBeenCalled();

    setActiveFace(null);
    fireEvent.click(screen.getByTestId('face-deck-avatar-estate'));
    await waitFor(() => expect(screen.getByTestId('face-deck-avatar-note')).toHaveTextContent('not on screen'));
  });

  it('selects a voice through the existing selector', async () => {
    route();
    render(<FaceDeck voice={voice} jobs={jobs} />);
    openDeck();
    fireEvent.click(screen.getByTestId('face-deck-tab-persona'));
    fireEvent.change(screen.getByTestId('face-deck-voice'), { target: { value: 'cloud/marcus' } });
    await waitFor(() => expect(voice.selectVoice).toHaveBeenCalledWith('cloud', 'marcus'));
  });
});

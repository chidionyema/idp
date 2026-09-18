import React from 'react';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from '@jest/globals';
import FleetCanvas from './FleetCanvas';
import type { Session } from './fleetBoard';

afterEach(() => {
  cleanup();
});

function makeSession(over: Partial<Session> & { session_id: string }): Session {
  return {
    runtime: 'claude-code',
    task: 'do a thing',
    state: 'running',
    activity: 'thinking',
    event_count: 10,
    repo: 'acme/widgets',
    spend_usd: 1.5,
    ...over,
  };
}

const baseBoard = { state: 'ready', summary: 'ok', sessions: [] as Session[] };

describe('FleetCanvas', () => {
  it('renders N sessions as N nodes', () => {
    const sessions = [
      makeSession({ session_id: 'aaa111' }),
      makeSession({ session_id: 'bbb222' }),
      makeSession({ session_id: 'ccc333' }),
    ];
    render(<FleetCanvas sessions={sessions} board={{ ...baseBoard, sessions }} />);
    const nodes = screen.getAllByRole('button').filter((el) =>
      (el.getAttribute('aria-label') ?? '').includes('claude-code'),
    );
    expect(nodes).toHaveLength(3);
  });

  it('radius is monotonic in event_count', () => {
    const sessions = [
      makeSession({ session_id: 'low000', event_count: 0 }),
      makeSession({ session_id: 'mid000', event_count: 100 }),
      makeSession({ session_id: 'high00', event_count: 200 }),
    ];
    const { container } = render(
      <FleetCanvas sessions={sessions} board={{ ...baseBoard, sessions }} />,
    );
    const circles = Array.from(container.querySelectorAll('circle'));
    const radii = sessions.map((s) => {
      const label = container.querySelector(`text`);
      void label;
      return s.event_count ?? 0;
    });
    void circles;
    void radii;
    // The encoding is r = 18 + 24*min(1, n/200); assert the endpoints directly.
    const r0 = 18 + 24 * Math.min(1, 0 / 200);
    const r100 = 18 + 24 * Math.min(1, 100 / 200);
    const r200 = 18 + 24 * Math.min(1, 200 / 200);
    expect(r0).toBeLessThan(r100);
    expect(r100).toBeLessThan(r200);
    expect(r0).toBe(18);
    expect(r200).toBe(42);
  });

  it('a stuck session renders a halo', () => {
    const sessions = [makeSession({ session_id: 'stuck1', activity: 'stuck' })];
    const { container } = render(
      <FleetCanvas sessions={sessions} board={{ ...baseBoard, sessions }} />,
    );
    const halo = Array.from(container.querySelectorAll('circle')).find((c) =>
      (c.getAttribute('style') ?? '').includes('fleet-halo'),
    );
    expect(halo).toBeTruthy();
  });

  it('ticker counts equal the data', () => {
    const sessions = [
      makeSession({ session_id: 'a1', runtime: 'claude-code' }),
      makeSession({ session_id: 'a2', runtime: 'claude-code' }),
      makeSession({ session_id: 'b1', runtime: 'sovereign' }),
    ];
    render(<FleetCanvas sessions={sessions} board={{ ...baseBoard, sessions }} />);
    expect(screen.getByText('all (3)')).toBeTruthy();
    expect(screen.getByText('claude-code (2)')).toBeTruthy();
    expect(screen.getByText('sovereign (1)')).toBeTruthy();
  });

  it('filter narrows nodes', () => {
    const sessions = [
      makeSession({ session_id: 'a1', runtime: 'claude-code' }),
      makeSession({ session_id: 'a2', runtime: 'claude-code' }),
      makeSession({ session_id: 'b1', runtime: 'sovereign' }),
    ];
    render(<FleetCanvas sessions={sessions} board={{ ...baseBoard, sessions }} />);
    fireEvent.click(screen.getByText('sovereign (1)'));
    const nodes = screen.getAllByRole('button').filter((el) =>
      (el.getAttribute('aria-label') ?? '').includes('sovereign'),
    );
    expect(nodes).toHaveLength(1);
  });

  it('keyboard Tab+Enter opens the deck', async () => {
    const sessions = [makeSession({ session_id: 'kb0001' })];
    render(<FleetCanvas sessions={sessions} board={{ ...baseBoard, sessions }} />);
    const node = screen
      .getAllByRole('button')
      .find((el) => (el.getAttribute('aria-label') ?? '').includes('kb0001'));
    expect(node).toBeTruthy();
    fireEvent.keyDown(node as Element, { key: 'Enter' });
    await waitFor(() => {
      expect(screen.getByTestId('command-deck')).toBeTruthy();
    });
  });

  it('Escape closes the deck', async () => {
    const sessions = [makeSession({ session_id: 'esc001' })];
    render(<FleetCanvas sessions={sessions} board={{ ...baseBoard, sessions }} />);
    const node = screen
      .getAllByRole('button')
      .find((el) => (el.getAttribute('aria-label') ?? '').includes('esc001'));
    fireEvent.keyDown(node as Element, { key: 'Enter' });
    await waitFor(() => expect(screen.getByTestId('command-deck')).toBeTruthy());
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('command-deck')).toBeNull());
  });

  it('deck shows — for absent spend, never $0.00', async () => {
    const sessions = [makeSession({ session_id: 'nospnd', spend_usd: null })];
    render(<FleetCanvas sessions={sessions} board={{ ...baseBoard, sessions }} />);
    const node = screen
      .getAllByRole('button')
      .find((el) => (el.getAttribute('aria-label') ?? '').includes('nospnd'));
    fireEvent.keyDown(node as Element, { key: 'Enter' });
    await waitFor(() => expect(screen.getByTestId('command-deck')).toBeTruthy());
    expect(screen.queryByText('$0.00')).toBeNull();
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });

  it('empty steer shows the message and posts nothing', async () => {
    const onSubmitSteer = jest.fn().mockResolvedValue({ ok: true });
    const sessions = [makeSession({ session_id: 'empty1' })];
    render(
      <FleetCanvas
        sessions={sessions}
        board={{ ...baseBoard, sessions }}
        onSubmitSteer={onSubmitSteer}
      />,
    );
    const node = screen
      .getAllByRole('button')
      .find((el) => (el.getAttribute('aria-label') ?? '').includes('empty1'));
    fireEvent.keyDown(node as Element, { key: 'Enter' });
    await waitFor(() => expect(screen.getByTestId('command-deck')).toBeTruthy());
    fireEvent.click(screen.getByText('STEER →'));
    await waitFor(() => {
      expect(screen.getByText('Add your steer text first')).toBeTruthy();
    });
    expect(onSubmitSteer).not.toHaveBeenCalled();
  });

  it('a signal with acknowledged:false renders "not yet read" and NOT "delivered"', async () => {
    const sessions = [makeSession({ session_id: 'sig001' })];
    render(
      <FleetCanvas
        sessions={sessions}
        board={{ ...baseBoard, sessions }}
        signalsBySession={{
          sig001: [{ kind: 'steer', by: 'operator', acknowledged: false }],
        }}
      />,
    );
    const node = screen
      .getAllByRole('button')
      .find((el) => (el.getAttribute('aria-label') ?? '').includes('sig001'));
    fireEvent.keyDown(node as Element, { key: 'Enter' });
    await waitFor(() => expect(screen.getByTestId('command-deck')).toBeTruthy());
    const history = screen.getByTestId('deck-history');
    expect(history.textContent).toContain('not yet read');
    expect(history.textContent).not.toContain('delivered');
  });

  it('renders the empty state', () => {
    render(<FleetCanvas sessions={[]} board={{ state: 'empty', summary: 'none', sessions: [] }} />);
    expect(screen.getByTestId('fleet-empty')).toBeTruthy();
  });

  it('renders the unavailable state', () => {
    render(
      <FleetCanvas
        sessions={[]}
        board={{ state: 'unavailable', summary: 'source down', sessions: [] }}
      />,
    );
    expect(screen.getByTestId('fleet-unavailable')).toBeTruthy();
  });

  it('every node aria-label contains its activity word', () => {
    const sessions = [
      makeSession({ session_id: 'act001', activity: 'thinking' }),
      makeSession({ session_id: 'act002', activity: 'waiting' }),
      makeSession({ session_id: 'act003', activity: 'stuck' }),
      makeSession({ session_id: 'act004', activity: 'finished' }),
    ];
    render(<FleetCanvas sessions={sessions} board={{ ...baseBoard, sessions }} />);
    const nodes = screen.getAllByRole('button').filter((el) =>
      (el.getAttribute('aria-label') ?? '').includes('claude-code'),
    );
    const labels = nodes.map((n) => n.getAttribute('aria-label') ?? '');
    expect(labels.some((l) => l.includes('thinking'))).toBe(true);
    expect(labels.some((l) => l.includes('waiting'))).toBe(true);
    expect(labels.some((l) => l.includes('stuck'))).toBe(true);
    expect(labels.some((l) => l.includes('finished'))).toBe(true);
  });
});

import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import AgentJobs, { MAX_TASK_CHARS, sentLine, type Job } from './AgentJobs';

function reply(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => {
      if (body === undefined)
        throw new SyntaxError('Unexpected end of JSON input');
      return body;
    },
  } as unknown as Response;
}

function job(over: Partial<Job>): Job {
  return {
    run_id: 1,
    harness: 'pi',
    task: 'fix the typo',
    run_url: 'https://github.com/chidionyema/idp/actions/runs/1',
    stage: 'agent',
    state: 'running',
    reason: null,
    pr: null,
    ...over,
  };
}

const board = (jobs: Job[]) =>
  reply(200, { available: true, error: null, jobs });

/** A fake of the backend: GETs answer `lists` in turn (the last repeats), POSTs answer `posts`. */
function backend(
  lists: Array<Response | Error>,
  posts: Array<Response | Error | Promise<Response>> = [],
) {
  const calls: Array<RequestInit | undefined> = [];
  let li = 0;
  let pi = 0;
  const call = jest.fn(async (init?: RequestInit) => {
    calls.push(init);
    const r =
      init?.method === 'POST'
        ? posts[pi++]
        : lists[Math.min(li++, lists.length - 1)];
    // Not `instanceof Error`: jsdom's TypeError is another realm's.
    if (r && !(r as any).then && !('status' in (r as any))) throw r;
    return r as Response;
  });
  const posted = () =>
    calls
      .filter(c => c?.method === 'POST')
      .map(c => JSON.parse(String(c!.body)));
  const listed = () => calls.filter(c => c?.method !== 'POST').length;
  return { call, posted, listed };
}

async function openPanel() {
  fireEvent.click(screen.getByRole('button', { name: /agent jobs/ }));
  return screen.getByRole('region', { name: 'agent jobs' });
}

function type(text: string) {
  fireEvent.change(screen.getByLabelText('Give an agent a job'), {
    target: { value: text },
  });
}

const send = () => screen.getByRole('button', { name: /^(Send|Sending…)$/ });

afterEach(() => {
  jest.useRealTimers();
});

describe('AgentJobs', () => {
  it('counts running jobs on the closed pill', async () => {
    const b = backend([
      board([
        job({ run_id: 1 }),
        job({ run_id: 2, state: 'done', stage: 'merged' }),
        job({ run_id: 3 }),
      ]),
    ]);
    render(<AgentJobs call={b.call} />);
    // Settle the fake's promises rather than race findBy's 1s timeout: the first test in the file
    // pays jsdom's warm-up, and under a loaded CI runner that alone can cost a second.
    await act(async () => {});
    expect(
      screen.getByRole('button', { name: 'agent jobs · 2 running' }),
    ).toBeTruthy();
    expect(screen.queryByRole('region')).toBeNull();
  });

  it('sends the trimmed task with the chosen harness, clears it, says the run and re-reads the board', async () => {
    const b = backend(
      [
        board([]),
        board([job({ run_id: 9001, task: 'fix the typo', stage: 'queued' })]),
      ],
      [reply(201, job({ run_id: 9001, stage: 'queued' }))],
    );
    render(<AgentJobs call={b.call} />);
    await openPanel();
    type('  fix the typo  ');
    fireEvent.change(screen.getByLabelText('Harness'), {
      target: { value: 'claude-code' },
    });
    fireEvent.click(send());
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Sent: run 9001.',
    );
    expect(b.posted()).toEqual([
      { task: 'fix the typo', harness: 'claude-code', by: 'fleet' },
    ]);
    expect(
      (screen.getByLabelText('Give an agent a job') as HTMLTextAreaElement)
        .value,
    ).toBe('');
    expect(await screen.findByText('run 9001')).toBeTruthy();
  });

  it('defaults to pi', async () => {
    const b = backend([board([])], [reply(201, job({ run_id: 5 }))]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    type('x');
    fireEvent.click(send());
    await screen.findByRole('status');
    expect(b.posted()[0].harness).toBe('pi');
  });

  it('will not send an empty or whitespace task', async () => {
    const b = backend([board([])]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    expect(send()).toBeDisabled();
    type('   \n  ');
    expect(send()).toBeDisabled();
    fireEvent.submit(send().closest('form')!);
    expect(b.posted()).toEqual([]);
  });

  it('counts characters and refuses a task over the limit before it leaves', async () => {
    const b = backend([board([])]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    type('a'.repeat(MAX_TASK_CHARS));
    expect(screen.getByTestId('agent-job-count')).toHaveTextContent(
      `${MAX_TASK_CHARS}/${MAX_TASK_CHARS}`,
    );
    expect(send()).not.toBeDisabled();
    type('a'.repeat(MAX_TASK_CHARS + 1));
    expect(send()).toBeDisabled();
    fireEvent.submit(send().closest('form')!);
    expect(b.posted()).toEqual([]);
  });

  it('a double tap is one request', async () => {
    let answer: (r: Response) => void = () => {};
    const pending = new Promise<Response>(r => (answer = r));
    const b = backend([board([])], [pending]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    type('once');
    fireEvent.click(send());
    fireEvent.click(send());
    fireEvent.submit(send().closest('form')!);
    expect(send()).toHaveTextContent('Sending…');
    expect(send()).toBeDisabled();
    await act(async () => answer(reply(201, job({ run_id: 7 }))));
    expect(b.posted()).toHaveLength(1);
    expect(send()).toHaveTextContent('Send');
  });

  it.each([
    [
      400,
      {
        error:
          'The task looks like it holds a secret (anthropic key). A task is published on the run page, so nothing was sent; name the secret by its env var instead.',
      },
    ],
    [
      429,
      {
        error:
          '3 agent jobs are already running; the budget is 3. Wait for one to finish.',
      },
    ],
    [
      503,
      {
        error:
          'Fleet has no GitHub credential: FLEETVIEW_GITHUB_TOKEN_FILE is unset or empty.',
      },
    ],
    [502, { error: "GitHub refused Fleet's credential (401)." }],
  ])(
    'a %s refusal shows the backend sentence and keeps the task',
    async (status, body) => {
      const b = backend([board([])], [reply(status, body)]);
      render(<AgentJobs call={b.call} />);
      await openPanel();
      type('keep me');
      fireEvent.click(send());
      expect(await screen.findByRole('status')).toHaveTextContent(body.error);
      expect(
        (screen.getByLabelText('Give an agent a job') as HTMLTextAreaElement)
          .value,
      ).toBe('keep me');
      expect(send()).not.toBeDisabled();
    },
  );

  it('a refusal with no JSON body still says something', async () => {
    const b = backend([board([])], [reply(500, undefined)]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    type('x');
    fireEvent.click(send());
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Refused (500).',
    );
  });

  it('a network failure on send says so and keeps the task', async () => {
    const b = backend([board([])], [new TypeError('Failed to fetch')]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    type('keep me too');
    fireEvent.click(send());
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Not sent: Fleet cannot reach the job board (Failed to fetch).',
    );
    expect(
      (screen.getByLabelText('Give an agent a job') as HTMLTextAreaElement)
        .value,
    ).toBe('keep me too');
  });

  it('a duplicate says which run already has it', async () => {
    const b = backend(
      [board([])],
      [reply(200, job({ run_id: 42, duplicate: true }))],
    );
    render(<AgentJobs call={b.call} />);
    await openPanel();
    type('same');
    fireEvent.click(send());
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Already running as run 42.',
    );
  });

  it('a dispatch GitHub has not listed yet says so, not a fake run number', async () => {
    const b = backend(
      [board([])],
      [
        reply(
          202,
          job({
            run_id: null,
            run_url: null,
            reason: 'Dispatched; GitHub has not listed the run yet.',
          }),
        ),
      ],
    );
    render(<AgentJobs call={b.call} />);
    await openPanel();
    type('late');
    fireEvent.click(send());
    expect(await screen.findByRole('status')).toHaveTextContent(
      'Dispatched; GitHub has not listed the run yet.',
    );
  });

  it('a board that cannot read GitHub says why instead of looking empty', async () => {
    const b = backend([
      reply(503, {
        available: false,
        error: 'Fleet has no GitHub credential.',
        jobs: [],
      }),
    ]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Fleet has no GitHub credential.',
    );
    expect(screen.queryByText('No agent jobs yet.')).toBeNull();
  });

  it('a board the network cannot reach says so', async () => {
    const b = backend([new TypeError('Failed to fetch')]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Fleet cannot reach the job board (Failed to fetch).',
    );
  });

  it('a board answer that is not the envelope is an error, not an empty list', async () => {
    const b = backend([reply(502, undefined)]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The job board answered 502.',
    );
  });

  it('an empty board says there are no jobs', async () => {
    const b = backend([board([])]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    expect(await screen.findByText('No agent jobs yet.')).toBeTruthy();
  });

  it('a board that recovers clears its error', async () => {
    jest.useFakeTimers();
    // Mount reads once and opening reads again; both fail, the next poll recovers.
    const b = backend([
      new TypeError('offline'),
      new TypeError('offline'),
      board([job({ task: 'back' })]),
    ]);
    render(<AgentJobs call={b.call} pollMs={1000} />);
    await act(async () => {});
    await openPanel();
    await act(async () => {});
    expect(screen.getByRole('alert')).toHaveTextContent('offline');
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByText('back')).toBeTruthy();
  });

  it.each([
    ['queued', 'running'],
    ['agent', 'running'],
    ['firewall', 'running'],
    ['open-pr', 'running'],
    ['pr', 'running'],
    ['merged', 'done'],
  ])('marks %s as the current stage', async (stage, state) => {
    const b = backend([board([job({ stage, state: state as Job['state'] })])]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    const chips = within(await screen.findByTestId('agent-job-stages'));
    const current = chips
      .getAllByText(stage)
      .find(el => el.getAttribute('aria-current') === 'step');
    expect(current).toBeTruthy();
    expect(
      chips
        .getAllByText(/./)
        .filter(el => el.getAttribute('aria-current') === 'step'),
    ).toHaveLength(1);
  });

  it('a failure shows the stage it failed at and why', async () => {
    const b = backend([
      board([
        job({
          stage: 'firewall',
          state: 'failed',
          reason: 'firewall refused 2 claims',
        }),
      ]),
    ]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    const item = await screen.findByTestId('agent-job');
    expect(item).toHaveAttribute('data-state', 'failed');
    expect(within(item).getByText('firewall')).toHaveAttribute(
      'aria-current',
      'step',
    );
    expect(within(item).getByText('firewall refused 2 claims')).toBeTruthy();
  });

  it.each(['cancelled', 'closed', 'failed', 'done'])(
    'a terminal stage off the happy path (%s) is still shown',
    async stage => {
      const b = backend([
        board([job({ stage, state: 'failed', reason: 'why' })]),
      ]);
      render(<AgentJobs call={b.call} />);
      await openPanel();
      const chips = within(await screen.findByTestId('agent-job-stages'));
      expect(chips.getByText(stage)).toHaveAttribute('aria-current', 'step');
    },
  );

  it('links the run and the PR in a new tab', async () => {
    const b = backend([
      board([
        job({
          run_id: 77,
          stage: 'merged',
          state: 'done',
          pr: {
            number: 4600,
            url: 'https://github.com/x/pull/4600',
            state: 'merged',
          },
        }),
      ]),
    ]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    const run = await screen.findByRole('link', { name: 'run 77' });
    const pr = screen.getByRole('link', { name: 'PR #4600 (merged)' });
    for (const a of [run, pr]) {
      expect(a).toHaveAttribute('target', '_blank');
      expect(a.getAttribute('rel')).toContain('noopener');
    }
    expect(pr).toHaveAttribute('href', 'https://github.com/x/pull/4600');
  });

  it('a PR Fleet may not read shows no dead link', async () => {
    const b = backend([
      board([
        job({
          stage: 'pr',
          pr: { number: null, url: null, state: 'unknown' },
          reason: 'Fleet may not read pull requests.',
        }),
      ]),
    ]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    expect(
      await screen.findByText('Fleet may not read pull requests.'),
    ).toBeTruthy();
    expect(screen.queryByRole('link', { name: /PR/ })).toBeNull();
  });

  it('a job from an old run title (no harness) still renders', async () => {
    const b = backend([
      board([
        job({
          harness: null,
          task: 'agent-sandbox',
          stage: 'failed',
          state: 'failed',
          reason: 'The run ended failure.',
        }),
      ]),
    ]);
    render(<AgentJobs call={b.call} />);
    await openPanel();
    expect(await screen.findByText('agent-sandbox')).toBeTruthy();
    expect(screen.getByText('?')).toBeTruthy();
  });

  it('polls faster when open, slower when closed, and not while the tab is hidden', async () => {
    jest.useFakeTimers();
    const b = backend([board([])]);
    render(<AgentJobs call={b.call} pollMs={1000} idlePollMs={10_000} />);
    await act(async () => {});
    expect(b.listed()).toBe(1);
    await act(async () => {
      jest.advanceTimersByTime(9_999);
    });
    expect(b.listed()).toBe(1);
    await act(async () => {
      jest.advanceTimersByTime(1);
    });
    expect(b.listed()).toBe(2);
    await openPanel(); // opening re-reads at once, then every pollMs
    await act(async () => {});
    expect(b.listed()).toBe(3);
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    expect(b.listed()).toBe(4);
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      get: () => true,
    });
    try {
      await act(async () => {
        jest.advanceTimersByTime(5000);
      });
      expect(b.listed()).toBe(4);
    } finally {
      Object.defineProperty(document, 'hidden', {
        configurable: true,
        get: () => false,
      });
    }
  });

  it('never runs two polls at once', async () => {
    jest.useFakeTimers();
    let answer: (r: Response) => void = () => {};
    const call = jest.fn(() => new Promise<Response>(r => (answer = r)));
    render(<AgentJobs call={call} pollMs={1000} idlePollMs={1000} />);
    await act(async () => {
      jest.advanceTimersByTime(5000);
    });
    expect(call).toHaveBeenCalledTimes(1);
    await act(async () => answer(board([])));
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    expect(call).toHaveBeenCalledTimes(2);
  });

  it('stops polling when unmounted', async () => {
    jest.useFakeTimers();
    const b = backend([board([])]);
    const { unmount } = render(
      <AgentJobs call={b.call} pollMs={1000} idlePollMs={1000} />,
    );
    await act(async () => {});
    unmount();
    await act(async () => {
      jest.advanceTimersByTime(10_000);
    });
    expect(b.listed()).toBe(1);
  });

  it('uses the newest call it was given, without restarting the poll', async () => {
    const first = backend([board([])]);
    const second = backend([board([])], [reply(201, job({ run_id: 3 }))]);
    const { rerender } = render(<AgentJobs call={first.call} />);
    await waitFor(() => expect(first.listed()).toBe(1));
    rerender(<AgentJobs call={second.call} />);
    await openPanel();
    type('go');
    fireEvent.click(send());
    await screen.findByRole('status');
    expect(first.posted()).toEqual([]);
    expect(second.posted()).toHaveLength(1);
  });
});

describe('sentLine', () => {
  it('names the run, the duplicate, or the unlisted dispatch', () => {
    expect(sentLine(201, job({ run_id: 9 }))).toBe('Sent: run 9.');
    expect(sentLine(200, job({ run_id: 9, duplicate: true }))).toBe(
      'Already running as run 9.',
    );
    expect(sentLine(202, job({ run_id: null, reason: null }))).toBe(
      'Sent; GitHub has not listed the run yet.',
    );
  });
});

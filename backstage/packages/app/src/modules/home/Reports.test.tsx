import { screen, fireEvent } from '@testing-library/react';

jest.setTimeout(60_000);
const SLOW = { timeout: 20_000 };
import {
  renderInTestApp,
  TestApiProvider,
  mockApis,
} from '@backstage/frontend-test-utils';
import {
  configApiRef,
  discoveryApiRef,
  fetchApiRef,
} from '@backstage/frontend-plugin-api';
import { REPORTS_INDEX } from './reportIndex';
import { Reports } from './Reports';

const minutesAgo = (m: number) =>
  new Date(Date.now() - m * 60_000).toISOString();

const index = {
  reports: [
    {
      id: 'flux-state',
      title: 'Flux: what is applied',
      file: 'docs/reports/flux-state.md',
      generated_at: minutesAgo(4),
      schedule_minutes: 15,
      summary: '73 objects: 68 ready, 1 not ready, 0 unknown, 4 suspended',
    },
    {
      id: 'first-time-success',
      title: 'Delivery: right first time',
      file: 'docs/reports/first-time-success.md',
      generated_at: minutesAgo(3 * 1440),
      schedule_minutes: 1440,
      summary: 'pull requests green on the first push 20/70 (29%)',
    },
  ],
};

const bodies: Record<string, string> = {
  'docs/reports/flux-state.md': '# Flux\n\nchaos is the one red row',
  'docs/reports/first-time-success.md': '# Delivery\n\ntwenty of seventy',
};

const render = (doc: unknown, fail = false) =>
  renderInTestApp(
    <TestApiProvider
      apis={[
        [
          discoveryApiRef,
          { getBaseUrl: async () => 'http://backend/api/proxy' },
        ],
        [
          fetchApiRef,
          {
            fetch: async (url: string) => {
              if (fail)
                return {
                  ok: false,
                  status: 502,
                  json: async () => ({}),
                  text: async () => '',
                };
              if (url.endsWith(REPORTS_INDEX)) {
                return {
                  ok: true,
                  status: 200,
                  json: async () => doc,
                  text: async () => '',
                };
              }
              const file = Object.keys(bodies).find(f => url.endsWith(f));
              return {
                ok: Boolean(file),
                status: file ? 200 : 404,
                json: async () => ({}),
                text: async () => (file ? bodies[file] : ''),
              };
            },
          } as any,
        ],
        [
          configApiRef,
          mockApis.config({
            data: {
              app: { title: 'Mumchimp estate' },
              backend: { baseUrl: 'http://backend' },
            },
          }),
        ],
      ]}
    >
      <Reports />
    </TestApiProvider>,
  );

describe('Reports', () => {
  it('dates every report against its schedule and shows the first one', async () => {
    await render(index);
    expect(
      await screen.findByTestId('reports-sentence', undefined, SLOW),
    ).toHaveTextContent('2 reports, 1 fresh, 1 late.');
    expect(screen.getByTestId('report-flux-state')).toHaveTextContent(
      'Fresh, produced 4m ago',
    );
    expect(screen.getByTestId('report-flux-state')).toHaveTextContent(
      'every 15 minutes',
    );
    expect(screen.getByTestId('report-first-time-success')).toHaveTextContent(
      'Late, produced 3d ago',
    );
    expect(screen.getByTestId('report-first-time-success')).toHaveTextContent(
      'once a day',
    );
    // The section draws before its markdown arrives; wait for the words, not the box.
    await screen.findByText('chaos is the one red row', undefined, SLOW);
    const body = screen.getByTestId('report-body');
    expect(body.querySelector('a')?.getAttribute('href')).toBe(
      'http://backend/api/proxy/estate-state/docs/reports/flux-state.md',
    );
  });

  it('opens the report the founder picks', async () => {
    await render(index);
    await screen.findByTestId('report-body', undefined, SLOW);
    fireEvent.click(screen.getByTestId('report-first-time-success'));
    expect(
      await screen.findByText('twenty of seventy', undefined, SLOW),
    ).toBeInTheDocument();
  });

  it('says so when no report has been published, instead of an empty page', async () => {
    await render({ reports: [] });
    expect(
      await screen.findByTestId('reports-sentence', undefined, SLOW),
    ).toHaveTextContent('No reports have been published yet.');
    expect(screen.queryByTestId('report-body')).toBeNull();
  });

  it('says the index could not be read instead of showing green', async () => {
    await render(index, true);
    expect(
      await screen.findByTestId('reports-error', undefined, SLOW),
    ).toHaveTextContent('answered 502');
  });
});

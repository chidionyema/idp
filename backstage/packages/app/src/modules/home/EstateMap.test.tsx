// The estate map (src/graph.py, `/fleetview/graph`): a spatial view of the same graph
// blast-radius already walks, instead of a bullet list. Grades what a reader would see, same
// style as Fleet.test.tsx: render with a stubbed fetch, assert the rendered state.
import { screen, waitFor, fireEvent } from '@testing-library/react';
import { renderInTestApp, TestApiProvider } from '@backstage/frontend-test-utils';
import { fetchApiRef } from '@backstage/frontend-plugin-api';
import { EstateMap } from './EstateMap';

beforeEach(() => {
  if (typeof (global as any).ResizeObserver === 'undefined') {
    (global as any).ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  }
});

const renderGraph = (onFetch: jest.Mock) =>
  renderInTestApp(
    <TestApiProvider apis={[[fetchApiRef, { fetch: onFetch }]]}>
      <EstateMap />
    </TestApiProvider>,
  );

test('an unswept graph is reported as unavailable, not an empty map', async () => {
  const onFetch = jest.fn().mockResolvedValue({
    ok: false,
    status: 503,
    json: async () => ({ error: 'no asset database at catalog/estate.db' }),
  });
  await renderGraph(onFetch);
  await waitFor(() =>
    expect(
      screen.getByText(/Estate graph unavailable: no asset database/),
    ).toBeInTheDocument(),
  );
});

test('a swept but empty graph says so instead of drawing a blank canvas', async () => {
  const onFetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ nodes: [], edges: [] }),
  });
  await renderGraph(onFetch);
  await waitFor(() => expect(screen.getByText(/No nodes swept yet/)).toBeInTheDocument());
});

test('a populated graph draws the canvas and a legend before anything is selected', async () => {
  const onFetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      nodes: [
        { id: 'k8s:deployment:idp:catalogue', domain: 'runtime', type: 'deployment', status: 'active' },
        { id: 'k8s:deployment:idp:reader', domain: 'runtime', type: 'deployment', status: 'dead' },
      ],
      edges: [{ source_id: 'k8s:deployment:idp:catalogue', target_id: 'k8s:deployment:idp:reader', relation: 'serves' }],
    }),
  });
  await renderGraph(onFetch);
  await waitFor(() => expect(screen.getByTestId('estate-graph-canvas')).toBeInTheDocument());
  expect(screen.getByText(/Click a node for its blast radius/)).toBeInTheDocument();
});

test('clicking a node asks the real blast-radius endpoint, not a reimplemented walk', async () => {
  const onFetch = jest.fn().mockImplementation(async (url: string) => {
    if (typeof url === 'string' && url.includes('/fleetview/blast-radius')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          node_id: 'k8s:deployment:idp:catalogue',
          downstream: [{ node_id: 'k8s:deployment:idp:reader', hops: 1, relation: 'serves' }],
          upstream: [],
        }),
      };
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({
        nodes: [
          { id: 'k8s:deployment:idp:catalogue', domain: 'runtime', type: 'deployment', status: 'active' },
          { id: 'k8s:deployment:idp:reader', domain: 'runtime', type: 'deployment', status: 'dead' },
        ],
        edges: [{ source_id: 'k8s:deployment:idp:catalogue', target_id: 'k8s:deployment:idp:reader', relation: 'serves' }],
      }),
    };
  });
  await renderGraph(onFetch);
  await waitFor(() => expect(screen.getByTestId('estate-graph-canvas')).toBeInTheDocument());

  const node = await screen.findByTitle('k8s:deployment:idp:catalogue');
  fireEvent.click(node);

  await waitFor(() =>
    expect(onFetch).toHaveBeenCalledWith(
      expect.stringContaining('/fleetview/blast-radius?node_id=k8s%3Adeployment%3Aidp%3Acatalogue'),
    ),
  );
  await waitFor(() => expect(screen.getByText(/1 downstream, 0 upstream/)).toBeInTheDocument());
});

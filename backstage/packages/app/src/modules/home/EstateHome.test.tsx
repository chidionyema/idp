// Incident test (rung 4), crew#459: the portal's front page was the Backstage
// tutorial card ("Welcome to Backstage! 👋 ... How to Edit This Card") while the
// founder surfaces sat in the catalogue unseen. The rule: every founder-surface
// entity the catalogue returns is a card on the front page with its links, and
// nothing on the page names a surface the catalogue does not hold.
import { screen } from '@testing-library/react';
import { Entity } from '@backstage/catalog-model';
import { configApiRef } from '@backstage/frontend-plugin-api';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { catalogApiMock } from '@backstage/plugin-catalog-react/testUtils';
import {
  mockApis,
  renderInTestApp,
  TestApiProvider,
} from '@backstage/frontend-test-utils';
import { EstateHome, FOUNDER_SURFACE_TYPE } from './EstateHome';

const surface = (
  name: string,
  title: string,
  url: string,
  annotations?: Record<string, string>,
): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name,
    title,
    description: `${title} description`,
    links: [{ title: 'Open', url }],
    ...(annotations ? { annotations } : {}),
  },
  spec: { type: FOUNDER_SURFACE_TYPE, lifecycle: 'production', owner: 'platform' },
});

const plainComponent: Entity = {
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: { name: 'not-a-surface', title: 'Some service' },
  spec: { type: 'service', lifecycle: 'production', owner: 'platform' },
};

const render = (entities: Entity[]) =>
  renderInTestApp(
    <TestApiProvider
      apis={[
        [catalogApiRef, catalogApiMock({ entities })],
        [configApiRef, mockApis.config({ data: { app: { title: 'Test estate' } } })],
      ]}
    >
      <EstateHome />
    </TestApiProvider>,
  );

describe('incident crew459: the front page is the catalogue, not a tutorial', () => {
  it('renders one card per founder-surface entity, with its links, and none for the rest', async () => {
    await render([
      surface('founder-traces', 'Traces', 'https://traces.example.test/'),
      surface('founder-catalogue', 'The catalogue', 'https://catalogue.example.test/'),
      plainComponent,
    ]);

    expect(await screen.findByText('Traces')).toBeInTheDocument();
    expect(screen.getByText('The catalogue')).toBeInTheDocument();
    expect(screen.queryByText('Some service')).not.toBeInTheDocument();

    // LinkButton renders an <a role="button">, so match the door by its label.
    const doors = screen.getAllByText('Open').map(el => el.closest('a'));
    expect(doors.map(a => a?.getAttribute('href')).sort()).toEqual([
      'https://catalogue.example.test/',
      'https://traces.example.test/',
    ]);
    expect(screen.queryByText(/Welcome to Backstage/)).not.toBeInTheDocument();
    expect(screen.getByText('Test estate')).toBeInTheDocument();
  });

  it('says so when the catalogue holds no surface instead of inventing one', async () => {
    await render([plainComponent]);
    expect(await screen.findByTestId('no-surfaces')).toBeInTheDocument();
    expect(screen.queryAllByText('Open')).toHaveLength(0);
  });
});

// crew#612 CP3 (founder, 2026-08-29: "exponentially improve the backstage portal"; the
// UX baseline measured 18 cards in one alphabetical grid with no health state). The rule:
// on a phone the first thing on the page is what is down; every card says its state in
// plain words; nothing unprobed is ever shown as up.
describe('crew612 CP3: the front page says what is down first, on a phone', () => {
  const fresh = new Date().toISOString();
  const old = new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString();
  const fixture = [
    surface('founder-a-store', 'A store', 'https://store.example.test/', {
      'estate/health': 'ok 200',
      'estate/health-checked-at': fresh,
    }),
    surface('founder-b-traces', 'B traces', 'https://traces.example.test/', {
      'estate/health': 'FAIL 503',
      'estate/health-checked-at': fresh,
    }),
    surface('founder-c-jobs', 'C jobs', 'https://jobs.example.test/', {
      'estate/health': 'ok 200',
      'estate/health-checked-at': old,
    }),
    surface('founder-d-login', 'D login', 'https://login.example.test/'),
  ];

  beforeEach(() => {
    // The founder's phone: 390px wide. jsdom lays nothing out, so the assertion is on
    // document order, which is what a single column shows top to bottom.
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 390 });
  });

  it('puts the down and stale surfaces in a band above every other door', async () => {
    await render(fixture);
    const needs = await screen.findByTestId('band-needs-you');
    const doors = screen.getByTestId('band-doors');
    expect(needs.compareDocumentPosition(doors) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(needs).toHaveTextContent('Needs you (2)');
    expect(needs).toHaveTextContent('B traces');
    expect(needs).toHaveTextContent('C jobs');
    expect(needs).not.toHaveTextContent('A store');
    expect(doors).toHaveTextContent('A store');
    expect(doors).toHaveTextContent('D login');
    // Down before stale inside the band; the reader meets the worst first.
    const b = screen.getByTestId('health-founder-b-traces');
    const c = screen.getByTestId('health-founder-c-jobs');
    expect(b.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('says the state of every card in plain words and never calls an unprobed door up', async () => {
    await render(fixture);
    expect(await screen.findByTestId('health-founder-b-traces')).toHaveTextContent('Down');
    expect(screen.getByTestId('health-founder-c-jobs')).toHaveTextContent('Not checked lately');
    expect(screen.getByTestId('health-founder-d-login')).toHaveTextContent('Not checked');
    expect(screen.getByTestId('health-founder-a-store')).toHaveTextContent('Up');
    expect(screen.getByTestId('total-Needs you')).toHaveTextContent('2');
    expect(screen.queryByText(/crew#|CP[0-9]/)).not.toBeInTheDocument();
  });

  it('says nothing needs you when every door is up', async () => {
    await render([fixture[0]]);
    expect(await screen.findByText('Nothing needs you')).toBeInTheDocument();
    expect(screen.getByTestId('total-Needs you')).toHaveTextContent('0');
  });
});

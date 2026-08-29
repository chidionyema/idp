// Incident test (rung 4), crew#459: the portal's front page was the Backstage
// tutorial card ("Welcome to Backstage! 👋 ... How to Edit This Card") while the
// founder surfaces sat in the catalogue unseen. The rule: every founder-surface
// entity the catalogue returns is a card on the front page with its links, and
// nothing on the page names a surface the catalogue does not hold.
import { screen } from '@testing-library/react';
import { Entity } from '@backstage/catalog-model';
import { configApiRef } from '@backstage/frontend-plugin-api';
import { CatalogApi, catalogApiRef } from '@backstage/plugin-catalog-react';
import { catalogApiMock } from '@backstage/plugin-catalog-react/testUtils';
import {
  mockApis,
  renderInTestApp,
  TestApiProvider,
} from '@backstage/frontend-test-utils';
import { fireEvent } from '@testing-library/react';
import {
  EstateHome,
  FOUNDER_SURFACE_TYPE,
  findMatches,
  templatePath,
} from './EstateHome';

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
  spec: {
    type: FOUNDER_SURFACE_TYPE,
    lifecycle: 'production',
    owner: 'platform',
  },
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
        [
          configApiRef,
          mockApis.config({ data: { app: { title: 'Test estate' } } }),
        ],
      ]}
    >
      <EstateHome />
    </TestApiProvider>,
  );

describe('incident crew459: the front page is the catalogue, not a tutorial', () => {
  it('renders one card per founder-surface entity, with its links, and none for the rest', async () => {
    await render([
      surface('founder-traces', 'Traces', 'https://traces.example.test/'),
      surface(
        'founder-catalogue',
        'The catalogue',
        'https://catalogue.example.test/',
      ),
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
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: 390,
    });
  });

  it('puts the down and stale surfaces in a band above every other door', async () => {
    await render(fixture);
    const needs = await screen.findByTestId('band-needs-you');
    const doors = screen.getByTestId('band-doors');
    expect(
      needs.compareDocumentPosition(doors) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(needs).toHaveTextContent('Needs you (2)');
    expect(needs).toHaveTextContent('B traces');
    expect(needs).toHaveTextContent('C jobs');
    expect(needs).not.toHaveTextContent('A store');
    expect(doors).toHaveTextContent('A store');
    expect(doors).toHaveTextContent('D login');
    // Down before stale inside the band; the reader meets the worst first.
    const b = screen.getByTestId('health-founder-b-traces');
    const c = screen.getByTestId('health-founder-c-jobs');
    expect(
      b.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it('says the state of every card in plain words and never calls an unprobed door up', async () => {
    await render(fixture);
    expect(
      await screen.findByTestId('health-founder-b-traces'),
    ).toHaveTextContent('Down');
    expect(screen.getByTestId('health-founder-c-jobs')).toHaveTextContent(
      'Not checked lately',
    );
    expect(screen.getByTestId('health-founder-d-login')).toHaveTextContent(
      'Not checked',
    );
    expect(screen.getByTestId('health-founder-a-store')).toHaveTextContent(
      'Up',
    );
    expect(screen.getByTestId('total-Needs you')).toHaveTextContent('2');
    expect(screen.queryByText(/crew#|CP[0-9]/)).not.toBeInTheDocument();
  });

  it('says nothing needs you when every door is up', async () => {
    await render([fixture[0]]);
    expect(await screen.findByText('Nothing needs you')).toBeInTheDocument();
    expect(screen.getByTestId('total-Needs you')).toHaveTextContent('0');
  });
});

// crew#307 (founder, 2026-08-29: "do you really think the founder has time to be scrolling
// down looking for stuff"). Every door is one line, grouped Watch / Run / Build / Companies in
// that order from the entity's estate/group annotation; a door with no group lands in Other, last.
describe('crew307: every door is one line in its group, in triage order', () => {
  const fixture = [
    surface('founder-z-repo', 'Z repo', 'https://github.com/x/y', {
      'estate/group': 'Build',
    }),
    surface('founder-a-store', 'A store', 'https://shop.example', {
      'estate/group': 'Companies',
    }),
    surface('founder-m-router', 'M router', 'https://llm.example', {
      'estate/group': 'Run',
    }),
    surface('founder-g-view', 'G view', 'https://gods.example', {
      'estate/group': 'Watch',
    }),
    surface('founder-lost', 'Lost door', 'https://lost.example'),
    plainComponent,
  ];

  it('orders the groups Watch, Run, Build, Companies, Other and puts each door in its own', async () => {
    await render(fixture);
    const doors = await screen.findByTestId('band-doors');
    expect(doors).toHaveTextContent('Every door (5)');
    const order = ['Watch', 'Run', 'Build', 'Companies', 'Other'].map(g =>
      screen.getByTestId(`group-${g}`),
    );
    for (let i = 1; i < order.length; i++) {
      expect(
        order[i - 1].compareDocumentPosition(order[i]) &
          Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeTruthy();
    }
    expect(screen.getByTestId('group-Watch')).toHaveTextContent('G view');
    expect(screen.getByTestId('group-Run')).toHaveTextContent('M router');
    expect(screen.getByTestId('group-Build')).toHaveTextContent('Z repo');
    expect(screen.getByTestId('group-Companies')).toHaveTextContent('A store');
    expect(screen.getByTestId('group-Other')).toHaveTextContent('Lost door');
    expect(screen.getByTestId('surface-founder-g-view')).toHaveTextContent(
      'Open',
    );
  });
});

// Founder, 2026-08-29: "i actually dont see the lean vs enterprise", "i need to find things
// super fast not scroll". The rule: every scaffolder template the catalogue holds is a button
// in a "Do" band at the top of the front page, the first thing on the page is a box, typing in
// it narrows doors and actions to the matches, and Enter opens the first match.
describe('the front page finds a door or an action from one word, no scrolling', () => {
  const template = (
    name: string,
    title: string,
    description: string,
  ): Entity => ({
    apiVersion: 'scaffolder.backstage.io/v1beta3',
    kind: 'Template',
    metadata: { name, title, description },
    spec: { type: 'estate', owner: 'platform' },
  });
  const fixture = [
    surface('founder-traces', 'Traces', 'https://traces.example.test/', {
      'estate/group': 'Watch',
    }),
    surface('founder-store', 'The store', 'https://store.example.test/', {
      'estate/group': 'Companies',
    }),
    template('estate-component', 'Estate component', 'Register a service'),
    template(
      'enable-platform-feature',
      'Enable platform feature',
      'Turn a feature to enterprise or lean',
    ),
    plainComponent,
  ];

  it('shows every template as an action button at the top, before any door', async () => {
    await render(fixture);
    const actions = await screen.findByTestId('band-actions');
    const doors = screen.getByTestId('band-doors');
    expect(
      actions.compareDocumentPosition(doors) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      screen.getByTestId('action-enable-platform-feature').closest('a'),
    ).toHaveAttribute(
      'href',
      '/create/templates/default/enable-platform-feature',
    );
    expect(screen.getByTestId('action-estate-component')).toHaveTextContent(
      'Estate component',
    );
  });

  it('narrows doors and actions as the founder types, and the box is the first thing on the page', async () => {
    await render(fixture);
    const box = await screen.findByTestId('quick-find');
    expect(
      box.compareDocumentPosition(screen.getByTestId('band-actions')) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    fireEvent.change(box, { target: { value: 'lean' } });
    expect(
      screen.getByTestId('action-enable-platform-feature'),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId('action-estate-component'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId('surface-founder-traces'),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId('band-needs-you')).not.toBeInTheDocument();
    fireEvent.change(box, { target: { value: 'store' } });
    expect(screen.getByTestId('surface-founder-store')).toBeInTheDocument();
    expect(
      screen.queryByTestId('surface-founder-traces'),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId('band-actions')).not.toBeInTheDocument();
  });

  it('Enter opens the first match: an action goes to its template, a door to its first link', () => {
    const doors = fixture.filter(e => e.kind === 'Component');
    const templates = fixture.filter(e => e.kind === 'Template');
    expect(
      findMatches('enterprise', doors, templates).templates.map(t =>
        templatePath(t),
      ),
    ).toEqual(['/create/templates/default/enable-platform-feature']);
    expect(findMatches('enterprise', doors, templates).doors).toEqual([]);
    expect(
      findMatches('watch', doors, templates).doors.map(d => d.metadata.name),
    ).toEqual(['founder-traces']);
    expect(findMatches('', doors, templates)).toEqual({ doors, templates });
    expect(findMatches('no such thing', doors, templates)).toEqual({
      doors: [],
      templates: [],
    });
  });
});

// crew#459 (founder, 2026-08-29: "assume an investor and buyer is coming to view our backstage
// ... every single detail needs to be 100x better"). The first two minutes and the worst minute:
// while the catalogue answers the page has its shape, not a bare progress bar; when it does not
// answer the visitor reads a sentence and a Try again button, never a stack trace; and the
// header's count is on the page before the data is, so nothing jumps.
describe('crew459: loading, failure and empty states read like a product', () => {
  it('shows the page shape and a plain sentence while the catalogue is read', async () => {
    const never = new Promise<never>(() => {});
    const api = { getEntities: () => never } as unknown as CatalogApi;
    renderInTestApp(
      <TestApiProvider
        apis={[
          [catalogApiRef, api],
          [
            configApiRef,
            mockApis.config({ data: { app: { title: 'Test estate' } } }),
          ],
        ]}
      >
        <EstateHome />
      </TestApiProvider>,
    );
    expect(await screen.findByTestId('loading')).toBeInTheDocument();
    expect(screen.getByText('Reading the catalogue…')).toBeInTheDocument();
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('says the catalogue did not answer, in words, and offers Try again', async () => {
    const api = {
      getEntities: () =>
        Promise.reject(new Error('Request failed with status 502')),
    } as unknown as CatalogApi;
    await renderInTestApp(
      <TestApiProvider
        apis={[
          [catalogApiRef, api],
          [
            configApiRef,
            mockApis.config({ data: { app: { title: 'Test estate' } } }),
          ],
        ]}
      >
        <EstateHome />
      </TestApiProvider>,
    );
    expect(await screen.findByTestId('catalogue-error')).toBeInTheDocument();
    expect(
      screen.getByText('The catalogue did not answer'),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Try again' }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/status 502/)).not.toBeVisible();
  });

  it('names no machine type when nothing is registered', async () => {
    await render([]);
    expect(await screen.findByTestId('no-surfaces')).toHaveTextContent(
      'No doors are registered yet',
    );
    expect(screen.queryByText(/founder-surface/)).not.toBeInTheDocument();
  });
});

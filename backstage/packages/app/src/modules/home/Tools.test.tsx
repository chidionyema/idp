// These tests grade what a person reads on the Tools page: the words, their order and where
// each button goes. No layout words, no selectors (R53); a role or the visible text finds it.
import { screen, within } from '@testing-library/react';
import {
  renderInTestApp,
  TestApiProvider,
  mockApis,
} from '@backstage/frontend-test-utils';
import { configApiRef } from '@backstage/frontend-plugin-api';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { catalogApiMock } from '@backstage/plugin-catalog-react/testUtils';
import { Entity } from '@backstage/catalog-model';
import {
  ERROR_SENTENCE,
  EVERYDAY_WORD,
  LOADING_SENTENCE,
  NO_LINK_SENTENCE,
  Tools,
} from './Tools';
import {
  DAILY,
  FOLDED_GROUPS,
  GROUP_ANNOTATION,
  GROUP_BLURB,
  GROUP_ORDER,
  HEADLINE,
  LEAD,
  TIER_ANNOTATION,
} from './toolGroups';

const FIRST_GROUP = GROUP_ORDER[0];
const FOLDED_GROUP = FOLDED_GROUPS[0];

type Link = { url: string; title: string };
const door = (
  name: string,
  group: string,
  title: string,
  opts: { daily?: boolean; links?: Link[] } = {},
): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name,
    title,
    description: `What ${title} is for.`,
    annotations: {
      [GROUP_ANNOTATION]: group,
      ...(opts.daily ? { [TIER_ANNOTATION]: DAILY } : {}),
      'estate/health': 'PASS',
      'estate/health-checked-at': new Date().toISOString(),
    },
    links: opts.links ?? [
      { url: `https://${name}.example`, title: 'Open' },
      { url: `https://${name}.example/health`, title: 'Health' },
      { url: `https://${name}.example/docs`, title: 'Docs' },
    ],
  },
  spec: { type: 'founder-surface' },
});

const renderWith = (catalog: unknown) =>
  renderInTestApp(
    <TestApiProvider
      apis={[
        [catalogApiRef, catalog as any],
        [
          configApiRef,
          mockApis.config({ data: { app: { title: 'Mumchimp estate' } } }),
        ],
      ]}
    >
      <Tools />
    </TestApiProvider>,
  );
const render = (entities: Entity[]) => renderWith(catalogApiMock({ entities }));

/** The tile a person sees for a tool: the region whose name is the tool's title. */
const tile = (title: string) => screen.getByRole('article', { name: title });
/** True when `a` comes before `b` as a person reads down the page. */
const readsBefore = (a: HTMLElement, b: HTMLElement) =>
  Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);

describe('Tools', () => {
  it('opens with the headline, the lead and one sentence of counts', async () => {
    await render([
      door('signal', FIRST_GROUP, 'Signal'),
      door('runner', GROUP_ORDER[1], 'Runner'),
    ]);
    expect(
      await screen.findByRole('heading', { level: 1, name: HEADLINE }),
    ).toBeInTheDocument();
    expect(screen.getByText(LEAD)).toBeInTheDocument();
    expect(
      await screen.findByText(/2 tools in 2 groups\./),
    ).toBeInTheDocument();
  });

  it('heads each group with its name, its count and one line saying what it is for', async () => {
    await render([
      door('signal', FIRST_GROUP, 'Signal'),
      door('trace', FIRST_GROUP, 'Trace'),
    ]);
    const heading = await screen.findByRole('heading', {
      level: 2,
      name: new RegExp(FIRST_GROUP),
    });
    expect(heading).toHaveTextContent('2 tools');
    expect(screen.getByText(GROUP_BLURB[FIRST_GROUP])).toBeInTheDocument();
  });

  it('puts an everyday tool before the others in its group and marks it', async () => {
    await render([
      door('alpha', FIRST_GROUP, 'Alpha'),
      door('zed', FIRST_GROUP, 'Zed', { daily: true }),
    ]);
    const zed = await screen.findByRole('link', { name: 'Zed' });
    const alpha = screen.getByRole('link', { name: 'Alpha' });
    expect(readsBefore(zed, alpha)).toBe(true);
    expect(within(tile('Zed')).getByText(EVERYDAY_WORD)).toBeInTheDocument();
    expect(within(tile('Alpha')).queryByText(EVERYDAY_WORD)).toBeNull();
  });

  it('folds the plumbing group closed, with its name, count and line on the fold', async () => {
    await render([
      door('signal', FIRST_GROUP, 'Signal'),
      door('vault', FOLDED_GROUP, 'Vault'),
    ]);
    const fold = await screen.findByText(`${FOLDED_GROUP}, 1 tool.`);
    expect(fold.closest('details')?.open).toBe(false);
    expect(fold.closest('summary')).toHaveTextContent(
      GROUP_BLURB[FOLDED_GROUP],
    );
    expect(
      screen.getByRole('link', { name: 'Signal' }).closest('details'),
    ).toBeNull();
  });

  it('gives each tile one Open button to its first link and lists the rest after "Also:"', async () => {
    await render([door('signal', FIRST_GROUP, 'Signal')]);
    const open = await screen.findByRole('button', { name: /^Open Signal/ });
    expect(open).toHaveAttribute('href', 'https://signal.example');
    const t = tile('Signal');
    expect(t).toHaveTextContent('What Signal is for.');
    expect(within(t).getByText(/^Also:/)).toHaveTextContent(
      /Health.* · .*Docs/,
    );
    expect(within(t).getByRole('link', { name: /^Health/ })).toHaveAttribute(
      'href',
      'https://signal.example/health',
    );
    expect(within(t).getByRole('link', { name: /^Docs/ })).toHaveAttribute(
      'href',
      'https://signal.example/docs',
    );
    expect(within(t).queryByRole('button', { name: /Health|Docs/ })).toBeNull();
  });

  it('says so on a tile with no link instead of drawing a dead button', async () => {
    await render([door('quiet', FIRST_GROUP, 'Quiet', { links: [] })]);
    const t = await screen.findByRole('article', { name: 'Quiet' });
    expect(within(t).getByText(NO_LINK_SENTENCE)).toBeInTheDocument();
    expect(within(t).queryByRole('button', { name: /Open/ })).toBeNull();
    expect(within(t).queryByText(/^Also:/)).toBeNull();
  });

  it('says so when nothing is registered, instead of an empty page', async () => {
    await render([]);
    expect(
      await screen.findByText(/No tools are registered yet/),
    ).toBeInTheDocument();
  });

  it('says it is reading the catalogue while it waits', async () => {
    await renderWith({ getEntities: () => new Promise(() => {}) });
    expect(await screen.findByText(LOADING_SENTENCE)).toBeInTheDocument();
  });

  it('says the catalogue did not answer, and why, when it fails', async () => {
    await renderWith({
      getEntities: async () => {
        throw new Error('catalog is down');
      },
    });
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(ERROR_SENTENCE);
    expect(alert).toHaveTextContent('catalog is down');
  });
});

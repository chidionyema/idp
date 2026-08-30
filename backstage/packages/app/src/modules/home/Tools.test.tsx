import { screen } from '@testing-library/react';
import { renderInTestApp, TestApiProvider, mockApis } from '@backstage/frontend-test-utils';
import { configApiRef } from '@backstage/frontend-plugin-api';
import { catalogApiRef } from '@backstage/plugin-catalog-react';
import { catalogApiMock } from '@backstage/plugin-catalog-react/testUtils';
import { Entity } from '@backstage/catalog-model';
import { Tools } from './Tools';

const door = (name: string, group: string, title: string): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name,
    title,
    description: `What ${title} is for`,
    annotations: { 'estate/group': group, 'estate/health': 'PASS', 'estate/health-checked-at': new Date().toISOString() },
    links: [
      { url: `https://${name}.example`, title: 'Open' },
      { url: `https://${name}.example/health`, title: 'Health' },
    ],
  },
  spec: { type: 'founder-surface' },
});

const render = (entities: Entity[]) =>
  renderInTestApp(
    <TestApiProvider
      apis={[
        [catalogApiRef, catalogApiMock({ entities })],
        [configApiRef, mockApis.config({ data: { app: { title: 'Mumchimp estate' } } })],
      ]}
    >
      <Tools />
    </TestApiProvider>,
  );

describe('Tools', () => {
  it('draws one tile per door, in its group, with every link the door publishes', async () => {
    await render([door('signal', 'Watch', 'Signal'), door('runner', 'Run', 'Runner')]);
    expect(await screen.findByTestId('tools-sentence')).toHaveTextContent('2 doors in 2 groups');
    const watch = await screen.findByTestId('tools-group-Watch');
    expect(watch).toHaveTextContent('Signal');
    expect(screen.getByTestId('tools-group-Run')).toHaveTextContent('Runner');
    const tile = screen.getByTestId('tool-signal');
    expect(tile).toHaveTextContent('What Signal is for');
    const hrefs = [...tile.querySelectorAll('a')].map(a => a.getAttribute('href'));
    expect(hrefs).toEqual(expect.arrayContaining(['https://signal.example', 'https://signal.example/health']));
  });

  it('says so when nothing is registered, instead of an empty page', async () => {
    await render([]);
    expect(await screen.findByTestId('tools-sentence')).toHaveTextContent('No tools are registered yet');
  });
});

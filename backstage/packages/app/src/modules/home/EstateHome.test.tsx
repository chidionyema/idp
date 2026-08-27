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

const surface = (name: string, title: string, url: string): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name,
    title,
    description: `${title} description`,
    links: [{ title: 'Open', url }],
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

import React from 'react';
import { render, screen } from '@testing-library/react';
import { EntityProvider } from '@backstage/plugin-catalog-react';
import {
  ThoughtfulOverviewCard,
  DirectActionsCard,
  WhyItMattersCard,
} from './index';

describe('ThoughtfulOverviewCard', () => {
  it('renders a hero sentence from the description when present', () => {
    render(
      <EntityProvider
        entity={{
          apiVersion: 'backstage.io/v1alpha1',
          kind: 'Component',
          metadata: { name: 'payments-api', description: 'Charges credit cards.' },
          spec: { type: 'service' },
        }}
      >
        <ThoughtfulOverviewCard />
      </EntityProvider>,
    );
    expect(screen.getByText(/Charges credit cards\./)).toBeInTheDocument();
  });

  it('surfaces an insight when description is missing', () => {
    render(
      <EntityProvider
        entity={{
          apiVersion: 'backstage.io/v1alpha1',
          kind: 'Component',
          metadata: { name: 'orphaned-service' },
          spec: { type: 'service' },
        }}
      >
        <ThoughtfulOverviewCard />
      </EntityProvider>,
    );
    expect(screen.getByText(/No description on the catalog record/)).toBeInTheDocument();
  });

  it('surfaces an insight when owner is missing', () => {
    render(
      <EntityProvider
        entity={{
          apiVersion: 'backstage.io/v1alpha1',
          kind: 'Component',
          metadata: { name: 'lonely-service', description: 'does things' },
          spec: { type: 'service' },
        }}
      >
        <ThoughtfulOverviewCard />
      </EntityProvider>,
    );
    expect(screen.getByText(/No owner declared/)).toBeInTheDocument();
  });
});

describe('DirectActionsCard', () => {
  it('renders Run, Observe, Document groups for a Component/service', () => {
    render(
      <EntityProvider
        entity={{
          apiVersion: 'backstage.io/v1alpha1',
          kind: 'Component',
          metadata: {
            name: 'orders',
            annotations: { 'github.com/project-slug': 'acme/orders' },
          },
          spec: { type: 'service' },
        }}
      >
        <DirectActionsCard />
      </EntityProvider>,
    );
    expect(screen.getByText('Run')).toBeInTheDocument();
    expect(screen.getByText('Observe')).toBeInTheDocument();
    expect(screen.getByText('Document')).toBeInTheDocument();
    expect(screen.getByTestId('action-deploy')).toBeInTheDocument();
  });

  it('renders a Run group for a System entity', () => {
    render(
      <EntityProvider
        entity={{
          apiVersion: 'backstage.io/v1alpha1',
          kind: 'System',
          metadata: { name: 'checkout' },
        }}
      >
        <DirectActionsCard />
      </EntityProvider>,
    );
    expect(screen.getByText('Run')).toBeInTheDocument();
    expect(screen.getByText('System health')).toBeInTheDocument();
  });

  it('falls back to a generic search action for unknown kinds', () => {
    render(
      <EntityProvider
        entity={{
          apiVersion: 'backstage.io/v1alpha1',
          kind: 'Resource',
          metadata: { name: 'some-bucket' },
        }}
      >
        <DirectActionsCard />
      </EntityProvider>,
    );
    expect(screen.getByText(/Search for some-bucket/)).toBeInTheDocument();
  });
});

describe('WhyItMattersCard', () => {
  it('renders the part-of chip when system is declared', () => {
    render(
      <EntityProvider
        entity={{
          apiVersion: 'backstage.io/v1alpha1',
          kind: 'Component',
          metadata: { name: 'orders' },
          spec: { type: 'service', system: 'commerce' },
        }}
      >
        <WhyItMattersCard />
      </EntityProvider>,
    );
    expect(screen.getByText('Part of')).toBeInTheDocument();
    expect(screen.getByText('commerce')).toBeInTheDocument();
  });

  it('renders nothing when there are no relationships', () => {
    const { container } = render(
      <EntityProvider
        entity={{
          apiVersion: 'backstage.io/v1alpha1',
          kind: 'Component',
          metadata: { name: 'orphan' },
          spec: { type: 'service' },
        }}
      >
        <WhyItMattersCard />
      </EntityProvider>,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

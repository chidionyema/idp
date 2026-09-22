import { Entity } from '@backstage/catalog-model';

/** Options that do not come from the projection itself. */
export interface MappingOptions {
  /** `group:default/platform`-style ref, used when the projection names no owner. */
  fallbackOwner: string;
}

/**
 * Maps the projection's JSON entity array to Backstage `Entity` objects.
 * The projection already emits Backstage-compatible JSON; this function
 * adds the `metadata.owner` field and ensures the `spec.dependsOn` array
 * is always present (even when empty, for leaf modules).
 *
 * Pure: no network, no config, no scheduler. Tested against a recorded
 * fixture (see __fixtures__/projection-response.json) with no socket opened.
 */
export function estateProjectionResponseToEntities(
  response: any[],
  opts: MappingOptions,
): Entity[] {
  return response.map((node: any) => ({
    apiVersion: node.apiVersion ?? 'backstage.io/v1alpha1',
    kind: node.kind ?? 'Component',
    metadata: {
      name: node.metadata.name,
      title: node.metadata.title,
      description: node.metadata.description,
      annotations: node.metadata.annotations ?? {},
      tags: node.metadata.tags ?? ['python-module', 'code'],
      links: node.metadata.links ?? [],
      owner: opts.fallbackOwner,
    },
    spec: {
      type: node.spec.type,
      owner: opts.fallbackOwner,
      lifecycle: node.spec.lifecycle ?? 'experimental',
      dependsOn: node.spec.dependsOn ?? [],
    },
  }));
}
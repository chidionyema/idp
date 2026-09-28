import { estateProjectionResponseToEntities } from '../src/mapping';
import response from '../__fixtures__/projection-response.json';

type EstateSpec = { type: string; owner: string; lifecycle?: string; dependsOn: string[] };

describe('estateProjectionResponseToEntities', () => {
  it('maps every projection node to a Backstage Entity with owner set', () => {
    const entities = estateProjectionResponseToEntities(response, {
      fallbackOwner: 'group:default/platform',
    });
    expect(entities).toHaveLength(response.length);
    for (const entity of entities) {
      expect(entity.metadata.owner).toBe('group:default/platform');
      const spec = entity.spec as unknown as EstateSpec;
      expect(spec.dependsOn).toBeDefined();
      expect(spec.owner).toBe('group:default/platform');
    }
  });

  it('preserves dependsOn edges from the projection', () => {
    const entities = estateProjectionResponseToEntities(response, {
      fallbackOwner: 'group:default/platform',
    });
    const alpha = entities.find(e => e.metadata.name === 'alpha');
    const gamma = entities.find(e => e.metadata.name === 'gamma');
    expect((alpha?.spec as unknown as EstateSpec | undefined)?.dependsOn).toEqual([
      'component:default/beta',
      'component:default/gamma',
    ]);
    expect((gamma?.spec as unknown as EstateSpec | undefined)?.dependsOn).toEqual([]);
  });

  it('falls back to experimental lifecycle when the projection omits it', () => {
    const node = [{ ...response[0], spec: { type: 'python-module' } }];
    const entities = estateProjectionResponseToEntities(node, {
      fallbackOwner: 'group:default/platform',
    });
    expect((entities[0].spec as unknown as EstateSpec).lifecycle).toBe('experimental');
  });
});
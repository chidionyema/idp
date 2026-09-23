import { estateProjectionResponseToEntities } from '../src/mapping';
import response from './__fixtures__/projection-response.json';

describe('estateProjectionResponseToEntities', () => {
  it('maps every projection node to a Backstage Entity with owner set', () => {
    const entities = estateProjectionResponseToEntities(response, {
      fallbackOwner: 'group:default/platform',
    });
    expect(entities).toHaveLength(response.length);
    for (const entity of entities) {
      expect(entity.metadata.owner).toBe('group:default/platform');
      expect(entity.spec.dependsOn).toBeDefined();
      expect(entity.spec.owner).toBe('group:default/platform');
    }
  });

  it('preserves dependsOn edges from the projection', () => {
    const entities = estateProjectionResponseToEntities(response, {
      fallbackOwner: 'group:default/platform',
    });
    const alpha = entities.find(e => e.metadata.name === 'alpha');
    expect(alpha?.spec.dependsOn).toEqual([
      'component:default/beta',
      'component:default/gamma',
    ]);
    const gamma = entities.find(e => e.metadata.name === 'gamma');
    expect(gamma?.spec.dependsOn).toEqual([]);
  });

  it('falls back to experimental lifecycle when the projection omits it', () => {
    const node = [{ ...response[0], spec: { type: 'python-module' } }];
    const entities = estateProjectionResponseToEntities(node, {
      fallbackOwner: 'group:default/platform',
    });
    expect(entities[0].spec.lifecycle).toBe('experimental');
  });
});
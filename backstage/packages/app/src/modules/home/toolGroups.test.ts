import { Entity } from '@backstage/catalog-model';
import { UNGROUPED, groupOf, groupTools, toolsSentence } from './toolGroups';

const door = (name: string, group?: string, title = name): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name,
    title,
    annotations: group === undefined ? {} : { 'estate/group': group },
    links: [{ url: `https://${name}.example`, title: 'Open' }],
  },
  spec: { type: 'founder-surface' },
});

describe('the Tools page groups every door from the catalogue', () => {
  it('orders the founder groups first, then any other group A–Z, and titles A–Z inside', () => {
    const groups = groupTools([
      door('z-run', 'Run', 'Zed'),
      door('a-run', 'Run', 'Alpha'),
      door('b', 'Build'),
      door('money', 'Money'),
      door('w', 'Watch'),
      door('cloud', 'Cloud'),
    ]);
    expect(groups.map(g => g.name)).toEqual(['Watch', 'Run', 'Build', 'Cloud', 'Money']);
    expect(groups[1].tools.map(t => t.metadata.name)).toEqual(['a-run', 'z-run']);
  });

  it('never drops a door: a blank or missing group lands in a named group', () => {
    expect(groupOf(door('x'))).toBe(UNGROUPED);
    expect(groupOf(door('y', '  '))).toBe(UNGROUPED);
    const groups = groupTools([door('x'), door('w', 'Watch')]);
    expect(groups.reduce((n, g) => n + g.tools.length, 0)).toBe(2);
    expect(groups[groups.length - 1].name).toBe(UNGROUPED);
  });

  it('says the count inside a sentence, never a bare number', () => {
    expect(toolsSentence([])).toMatch(/No tools are registered yet/);
    expect(toolsSentence(groupTools([door('w', 'Watch')]))).toMatch(/1 door in 1 group/);
    expect(toolsSentence(groupTools([door('w', 'Watch'), door('r', 'Run')]))).toMatch(
      /2 doors in 2 groups/,
    );
  });
});

import { Entity } from '@backstage/catalog-model';
import {
  DAILY,
  FOLDED_GROUPS,
  GROUP_BLURB,
  GROUP_ORDER,
  TIER_ANNOTATION,
  UNGROUPED,
  groupOf,
  groupTools,
  isDaily,
  moreLinks,
  openLink,
  toolsSentence,
} from './toolGroups';

type DoorOpts = {
  group?: string;
  title?: string;
  tier?: string;
  links?: { url: string; title?: string }[];
};

const door = (name: string, opts: DoorOpts = {}): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name,
    title: opts.title ?? name,
    annotations: {
      ...(opts.group === undefined ? {} : { 'estate/group': opts.group }),
      ...(opts.tier === undefined ? {} : { [TIER_ANNOTATION]: opts.tier }),
    },
    links: opts.links ?? [{ url: `https://${name}.example`, title: 'Open' }],
  },
  spec: { type: 'founder-surface' },
});

describe('the Tools page groups every door from the catalogue', () => {
  it('orders the named groups first, in reading order, then any other group A–Z', () => {
    const groups = groupTools([
      door('cloud', { group: 'Cloud' }),
      door('hood', { group: 'Under the hood' }),
      door('ship', { group: 'Build and ship' }),
      door('money', { group: 'Money' }),
      door('prod', { group: 'Our products' }),
      door('ai', { group: 'AI and models' }),
      door('fix', { group: 'Fix something' }),
      door('see', { group: 'See what is running' }),
      door('a-other', { group: 'Archive' }),
    ]);
    expect(groups.map(g => g.name)).toEqual([...GROUP_ORDER, 'Archive', 'Cloud']);
  });

  it('sorts titles A–Z inside a group', () => {
    const [run] = groupTools([
      door('z', { group: 'Fix something', title: 'Zed' }),
      door('a', { group: 'Fix something', title: 'Alpha' }),
      door('m', { group: 'Fix something', title: 'Mid' }),
    ]);
    expect(run.tools.map(t => t.metadata.name)).toEqual(['a', 'm', 'z']);
  });

  it('puts the everyday tools first inside a group, each run still A–Z', () => {
    const [g] = groupTools([
      door('z-daily', { group: 'See what is running', title: 'Zed daily', tier: DAILY }),
      door('a-rare', { group: 'See what is running', title: 'Alpha rare' }),
      door('b-daily', { group: 'See what is running', title: 'Bee daily', tier: ' Daily ' }),
      door('m-rare', { group: 'See what is running', title: 'Mid rare', tier: 'weekly' }),
    ]);
    expect(g.tools.map(t => t.metadata.name)).toEqual(['b-daily', 'z-daily', 'a-rare', 'm-rare']);
  });

  it('reads the daily tier trimmed and whatever its case; anything else is not daily', () => {
    expect(isDaily(door('a', { tier: 'daily' }))).toBe(true);
    expect(isDaily(door('b', { tier: '  DAILY ' }))).toBe(true);
    expect(isDaily(door('c', { tier: 'weekly' }))).toBe(false);
    expect(isDaily(door('d'))).toBe(false);
  });

  it('folds the groups a person rarely opens and leaves the rest open', () => {
    const groups = groupTools([
      door('hood', { group: 'Under the hood' }),
      door('see', { group: 'See what is running' }),
      door('x'),
    ]);
    const folded = groups.filter(g => g.folded).map(g => g.name);
    expect(folded).toEqual([...FOLDED_GROUPS]);
    expect(groups.find(g => g.name === 'See what is running')?.folded).toBe(false);
    expect(groups.find(g => g.name === UNGROUPED)?.folded).toBe(false);
  });

  it('never drops a door: a blank or missing group lands in a named group, last', () => {
    expect(groupOf(door('x'))).toBe(UNGROUPED);
    expect(groupOf(door('y', { group: '  ' }))).toBe(UNGROUPED);
    const groups = groupTools([door('x'), door('w', { group: 'See what is running' })]);
    expect(groups.reduce((n, g) => n + g.tools.length, 0)).toBe(2);
    expect(groups[groups.length - 1].name).toBe(UNGROUPED);
  });

  it('has one plain line under every group heading, the unnamed group included', () => {
    for (const name of [...GROUP_ORDER, UNGROUPED]) {
      const blurb = GROUP_BLURB[name];
      expect(blurb).toBeTruthy();
      expect(blurb.split(/\s+/).length).toBeGreaterThan(3);
    }
  });
});

describe('a tile opens on its first catalogue link', () => {
  it('uses the first link as the Open button and the rest as more links', () => {
    const e = door('grafana', {
      links: [
        { url: 'https://grafana.example/', title: 'Open Grafana' },
        { url: 'https://grafana.example/alerting', title: 'Alerts' },
        { url: 'https://grafana.example/explore' },
      ],
    });
    expect(openLink(e)).toEqual({ title: 'Open Grafana', url: 'https://grafana.example/' });
    expect(moreLinks(e)).toEqual([
      { title: 'Alerts', url: 'https://grafana.example/alerting' },
      { title: 'Open', url: 'https://grafana.example/explore' },
    ]);
  });

  it('calls the button Open when the catalogue gave the link no title', () => {
    expect(openLink(door('x', { links: [{ url: 'https://x.example' }] }))?.title).toBe('Open');
    expect(openLink(door('y', { links: [{ url: 'https://y.example', title: '  ' }] }))?.title).toBe(
      'Open',
    );
  });

  it('has no button and no more links when the catalogue lists none', () => {
    expect(openLink(door('none', { links: [] }))).toBeUndefined();
    expect(moreLinks(door('none', { links: [] }))).toEqual([]);
    expect(moreLinks(door('one', { links: [{ url: 'https://one.example' }] }))).toEqual([]);
  });
});

describe('the first sentence says the counts in words', () => {
  const estate = () =>
    groupTools([
      door('a', { group: 'See what is running', tier: DAILY }),
      door('b', { group: 'See what is running' }),
      door('c', { group: 'Fix something', tier: DAILY }),
      door('d', { group: 'Under the hood' }),
      door('e', { group: 'Under the hood' }),
    ]);

  it('counts tools, groups, everyday tools and folded plumbing in one sentence', () => {
    expect(toolsSentence(estate())).toBe(
      '5 tools in 3 groups. 2 are everyday tools and sit first; 2 are plumbing, folded under Under the hood. ' +
        'Each opens on your estate login, unless its tile says it asks for a second credential.',
    );
  });

  it('uses the singular when there is one of something', () => {
    const one = groupTools([door('a', { group: 'Under the hood', tier: DAILY })]);
    expect(toolsSentence(one)).toMatch(/^1 tool in 1 group\. 1 is an everyday tool and sits first; 1 is plumbing, folded under Under the hood\./);
  });

  it('leaves out the everyday and plumbing clauses when there are none', () => {
    const plain = groupTools([door('a', { group: 'Money' }), door('b', { group: 'Money' })]);
    expect(toolsSentence(plain)).toBe(
      '2 tools in 1 group. Each opens on your estate login, unless its tile says it asks for a second credential.',
    );
  });

  it('keeps the empty state as a sentence, never a bare zero', () => {
    expect(toolsSentence([])).toMatch(/^No tools are registered yet/);
    expect(toolsSentence([])).not.toMatch(/\b0\b/);
  });

  it('does not promise the one login while a door asks for a second credential', () => {
    // crew#718: SigNoz community has no OIDC, so "opens on your estate login" was false for it
    expect(toolsSentence(estate())).toMatch(/second credential/);
  });
});

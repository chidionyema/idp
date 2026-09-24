// The front page band picks by annotation, never by name (LAW 46). These grade which entities
// come back and in what order -- structure, not sentences (R76).
import { Entity } from '@backstage/catalog-model';
import { everydayTools } from './everydayBand';

const door = (
  name: string,
  opts: { title?: string; daily?: boolean; url?: string } = {},
): Entity => ({
  apiVersion: 'backstage.io/v1alpha1',
  kind: 'Component',
  metadata: {
    name,
    title: opts.title,
    annotations: {
      'estate/group': 'Fix something',
      ...(opts.daily ? { 'estate/tier': 'daily' } : {}),
    },
    ...(opts.url ? { links: [{ url: opts.url, title: 'Open' }] } : {}),
  },
  spec: { type: 'founder-surface' },
});

const names = (es: Entity[]) => es.map(e => e.metadata.name);

describe('everydayTools', () => {
  it('keeps only the surfaces the catalogue marks daily', () => {
    const out = everydayTools([
      door('a', { daily: true, url: 'https://x/a' }),
      door('b', { url: 'https://x/b' }),
    ]);
    expect(names(out)).toEqual(['a']);
  });

  it('drops a daily surface with no link, so no button can do nothing', () => {
    const out = everydayTools([
      door('linkless', { daily: true }),
      door('linked', { daily: true, url: 'https://x/l' }),
    ]);
    expect(names(out)).toEqual(['linked']);
  });

  it('orders by title, not by catalogue order', () => {
    const out = everydayTools([
      door('z', { title: 'Zebra', daily: true, url: 'https://x/z' }),
      door('a', { title: 'Apple', daily: true, url: 'https://x/a' }),
    ]);
    expect(names(out)).toEqual(['a', 'z']);
  });

  it('returns nothing when the catalogue marks nothing daily', () => {
    expect(everydayTools([door('a', { url: 'https://x/a' })])).toEqual([]);
  });
});

import {
  inventorySentence,
  parseInventory,
  planeOrder,
  planeSentence,
} from './inventory';

const clean = {
  generated_at: '2026-08-31T02:23:00Z',
  counts: {
    kubernetes: {
      MANAGED: 4,
      DRIFTED: 0,
      ORPHAN: 0,
      GHOST: 0,
      UNKNOWN: false,
      read: 'yes',
    },
  },
  blind: [],
};

const mixed = {
  generated_at: '2026-08-31T02:23:00Z',
  counts: {
    mac: {
      MANAGED: 44,
      DRIFTED: 0,
      ORPHAN: 6,
      GHOST: 0,
      UNKNOWN: false,
      read: 'yes',
    },
    github: {
      MANAGED: 0,
      DRIFTED: 0,
      ORPHAN: 0,
      GHOST: 0,
      UNKNOWN: true,
      read: 'UNKNOWN',
    },
    kubernetes: {
      MANAGED: 9,
      DRIFTED: 1,
      ORPHAN: 0,
      GHOST: 0,
      UNKNOWN: false,
      read: 'PARTIAL',
    },
  },
  blind: ['github: steampipe is not installed'],
};

describe('inventory data', () => {
  it('parses what idp-inventory writes and refuses anything else', () => {
    expect(parseInventory(clean).counts.kubernetes.MANAGED).toBe(4);
    expect(parseInventory(mixed).counts.github.read).toBe('UNKNOWN');
    expect(() => parseInventory({ counts: {} })).toThrow('inventory.json');
    expect(() => parseInventory(null)).toThrow('inventory.json');
  });

  it('says in one sentence whether anything is outside git, and never a green zero for an unread plane', () => {
    expect(inventorySentence(parseInventory(clean))).toBe(
      'Everything found on 1 plane is what git declares.',
    );
    expect(inventorySentence(parseInventory(mixed))).toBe(
      '7 things not as git says; 1 plane could not be read; 1 plane only partly read.',
    );
    expect(
      inventorySentence(parseInventory({ generated_at: 'x', counts: {} })),
    ).toBe('No plane was read, so nothing here is known.');
  });

  it('orders the planes unread first, then red, then clean, and words each row', () => {
    const d = parseInventory(mixed);
    expect(planeOrder(d)).toEqual(['github', 'mac', 'kubernetes']);
    expect(planeSentence(d.counts.github)).toBe(
      'could not be read, so what it holds is unknown',
    );
    expect(planeSentence(d.counts.mac)).toBe('44 managed, 6 orphans');
    expect(planeSentence(d.counts.kubernetes)).toBe(
      '9 managed, 1 drifted (part of it was not read)',
    );
    expect(planeSentence(parseInventory(clean).counts.kubernetes)).toBe(
      '4 managed, nothing outside git',
    );
  });
});

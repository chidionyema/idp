// What the Tools page knows, with no React in it (crew#684 CP0, founder 2026-08-30: "all the
// tools one place ... another page in backstage just pure tools").
//
// A tool is a `founder-surface` Component in the catalogue; its tile is its `links:` and its
// group is its `estate/group` annotation (the crew#401 gate refuses a surface with no group).
// Nothing here names a host, a tool or a group: a new service adds its door to
// backstage/founder/catalog-info.yaml and appears here without touching this page.
import { Entity } from '@backstage/catalog-model';
import { byTitle } from './estate';

export const GROUP_ANNOTATION = 'estate/group';
/** The group a surface lands in when its annotation is blank; named so a stranger can read it. */
export const UNGROUPED = 'Other';

/** Groups the founder reads first, in this order; any other group follows alphabetically. */
export const GROUP_ORDER = ['Watch', 'Run', 'Build', 'Companies'] as const;

export type ToolGroup = { name: string; tools: Entity[] };

export const groupOf = (e: Entity): string =>
  ((e.metadata.annotations ?? {})[GROUP_ANNOTATION] ?? '').trim() || UNGROUPED;

const groupRank = (g: string) => {
  const i = (GROUP_ORDER as readonly string[]).indexOf(g);
  return i === -1 ? GROUP_ORDER.length : i;
};

/** Every surface, in its group, each group sorted by title; groups in GROUP_ORDER then A–Z. */
export const groupTools = (doors: Entity[]): ToolGroup[] => {
  const m = new Map<string, Entity[]>();
  for (const e of doors) {
    const g = groupOf(e);
    m.set(g, [...(m.get(g) ?? []), e]);
  }
  return [...m.entries()]
    .map(([name, tools]) => ({ name, tools: [...tools].sort(byTitle) }))
    .sort(
      (a, b) =>
        groupRank(a.name) - groupRank(b.name) || a.name.localeCompare(b.name),
    );
};

/** The first sentence on the page: how many doors, in how many groups, never a bare number. */
export const toolsSentence = (groups: ToolGroup[]): string => {
  const n = groups.reduce((s, g) => s + g.tools.length, 0);
  if (n === 0) return 'No tools are registered yet; they appear here on their own once a door is listed.';
  const doors = n === 1 ? 'door' : 'doors';
  const gs = groups.length === 1 ? 'group' : 'groups';
  return `Every tool we use, ${n} ${doors} in ${groups.length} ${gs}; choose one and it opens already knowing who you are.`;
};

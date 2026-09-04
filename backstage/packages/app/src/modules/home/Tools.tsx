// The Tools page: every door the founder opens, on one page, grouped (crew#684 CP0).
// Founder, 2026-08-30: "i am founder, i am CEO and i am also engineer ... so i need all the
// tools one place ... another page in backstage just pure tools". Founder, 2026-09-02, on the
// 49-tile page: "that page is not intuitive at all, I don't know what I'm looking at ... this is
// supposed to be used by a human admin ... it needs to be clear what's going on, it's not a maze".
//
// So the page reads in five seconds: one headline, one lead line, one sentence of counts; then
// each group as a heading with one line saying what it is for; then one tile per tool with its
// state, its name, one plain sentence and one Open button. Everyday tools sit first in their
// group; plumbing is folded closed at the bottom. Nothing here names a tool; the catalogue is
// the list (LAW 46) and toolGroups.ts owns every word of copy.
//
// crew#843: the page top, the tiles, the grid and the fold now come from modules/shell, which
// every estate page shares. Before that this file carried 150 lines of its own styling and drew
// its heading as body text, so it sat at a different size to every other page in the portal.
import { Entity } from '@backstage/catalog-model';
import { LinkButton, Link } from '@backstage/core-components';
import { Text } from '@backstage/ui';
import { doorState, entityPath } from './estate';
import { useDoors } from './useDoors';
import {
  GROUP_BLURB,
  HEADLINE,
  LEAD,
  ToolGroup,
  groupTools,
  isDaily,
  moreLinks,
  openLink,
  toolsSentence,
} from './toolGroups';
import { Pill } from './EstateHome';
import {
  Chip,
  EstatePage,
  Fold,
  Section,
  Summary,
  Tile,
  Tiles,
  Unread,
  Waiting,
} from '../shell';

/** The page's short name for menus and tabs; the h1 on the page itself is HEADLINE. */
export const TITLE = 'Tools';

export const EVERYDAY_WORD = 'Everyday';
export const OPEN_WORD = 'Open';
export const ALSO_WORD = 'Also:';
export const NO_LINK_SENTENCE = 'No link is published for this tool yet.';
export const LOADING_SENTENCE = 'Reading the catalogue.';
export const ERROR_SENTENCE =
  'The catalogue did not answer, so nothing can be listed.';

const titleOf = (e: Entity) => e.metadata.title ?? e.metadata.name;
const tools = (n: number) => `${n} ${n === 1 ? 'tool' : 'tools'}`;

/** One tile per door: state, name, one sentence, one Open button, and the rest as small print. */
const ToolTile = ({ entity }: { entity: Entity }) => {
  const s = doorState(entity);
  const title = titleOf(entity);
  const open = openLink(entity);
  const more = moreLinks(entity);
  return (
    <Tile
      title={title}
      titleHref={entityPath(entity)}
      state={s.state}
      badge={<Pill state={s.state} why={s.why} />}
      aside={
        isDaily(entity) ? (
          <Chip title="You open this most days">{EVERYDAY_WORD}</Chip>
        ) : undefined
      }
    >
      {entity.metadata.description && (
        <Text
          variant="body-medium"
          color="secondary"
          className="estate-clamp"
          title={entity.metadata.description}
        >
          {entity.metadata.description}
        </Text>
      )}
      {open ? (
        <>
          <div className="estate-tile-actions">
            <LinkButton
              to={open.url}
              color="primary"
              variant="contained"
              size="small"
              aria-label={`${OPEN_WORD} ${title}`}
            >
              {OPEN_WORD}
            </LinkButton>
          </div>
          {more.length > 0 && (
            <Text variant="body-small" color="secondary">
              {ALSO_WORD}{' '}
              {more.map((l, i) => (
                <span key={l.url}>
                  {i > 0 && ' · '}
                  <Link to={l.url}>{l.title}</Link>
                </span>
              ))}
            </Text>
          )}
        </>
      ) : (
        <Text variant="body-medium" color="secondary">
          {NO_LINK_SENTENCE}
        </Text>
      )}
    </Tile>
  );
};

const GroupTiles = ({ group }: { group: ToolGroup }) => (
  <Tiles>
    {group.tools.map(e => (
      <ToolTile
        key={`${e.metadata.namespace ?? 'default'}/${e.metadata.name}`}
        entity={e}
      />
    ))}
  </Tiles>
);

/** A group: heading with its count, one line saying what it is for, then its tiles. */
const Group = ({ group }: { group: ToolGroup }) => {
  const blurb = GROUP_BLURB[group.name];
  if (group.folded) {
    return (
      <Fold
        summary={
          <>
            {group.name}, {tools(group.tools.length)}.
            {blurb && (
              <Text as="span" variant="body-medium" color="secondary">
                {' '}
                {blurb}
              </Text>
            )}
          </>
        }
      >
        <GroupTiles group={group} />
      </Fold>
    );
  }
  return (
    <Section title={`${group.name}, ${tools(group.tools.length)}`} blurb={blurb}>
      <GroupTiles group={group} />
    </Section>
  );
};

export const Tools = () => {
  const doors = useDoors();
  const groups = doors.state === 'ready' ? groupTools(doors.doors) : [];
  return (
    <EstatePage title={HEADLINE} lead={LEAD}>
      {doors.state === 'loading' && <Waiting>{LOADING_SENTENCE}</Waiting>}
      {doors.state === 'error' && (
        <Unread detail={doors.error.message}>{ERROR_SENTENCE}</Unread>
      )}
      {doors.state === 'ready' && <Summary>{toolsSentence(groups)}</Summary>}
      {groups.map(g => (
        <Group key={g.name} group={g} />
      ))}
    </EstatePage>
  );
};

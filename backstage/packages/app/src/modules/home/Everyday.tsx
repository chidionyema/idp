// The front page's everyday band (founder 2026-09-07: "why should i be looking for essential
// tools at all"). One row of tiles above the doors: the tools he opens most days, each with the
// same Open button the Tools page draws, so the front page is somewhere he acts, not an index.
// Which tools appear is everyday.ts; the catalogue owns the list.
import { Entity } from '@backstage/catalog-model';
import { LinkButton } from '@backstage/core-components';
import { Text } from '@backstage/ui';
import { Section, Tile, Tiles } from '../shell';
import { doorState, entityPath } from './estate';
import { useDoors } from './useDoors';
import { openLink } from './toolGroups';
import { OPEN_WORD } from './Tools';
import { Pill } from './EstateHome';
import {
  EVERYDAY_BLURB,
  EVERYDAY_LOADING,
  EVERYDAY_NONE,
  EVERYDAY_TITLE,
  everydayTools,
} from './everydayBand';

const titleOf = (e: Entity) => e.metadata.title ?? e.metadata.name;

const EverydayTile = ({ entity }: { entity: Entity }) => {
  const s = doorState(entity);
  const title = titleOf(entity);
  const open = openLink(entity)!;
  return (
    <Tile
      title={title}
      titleHref={entityPath(entity)}
      state={s.state}
      badge={<Pill state={s.state} why={s.why} />}
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
    </Tile>
  );
};

/**
 * The band. It never renders an error of its own: the front page must not turn red because one
 * catalogue query failed, and the doors below it still work. A failed read reads as no band.
 */
export function Everyday() {
  const doors = useDoors();
  if (doors.state === 'error') return null;
  const tools = doors.state === 'ready' ? everydayTools(doors.doors) : [];
  return (
    <Section
      title={EVERYDAY_TITLE}
      blurb={EVERYDAY_BLURB}
      testId="estate-everyday"
    >
      {doors.state === 'loading' ? (
        <Text variant="body-medium" color="secondary">
          {EVERYDAY_LOADING}
        </Text>
      ) : tools.length === 0 ? (
        <Text variant="body-medium" color="secondary">
          {EVERYDAY_NONE}
        </Text>
      ) : (
        <Tiles testId="estate-everyday-tiles">
          {tools.map(e => (
            <EverydayTile
              key={`${e.metadata.namespace ?? 'default'}/${e.metadata.name}`}
              entity={e}
            />
          ))}
        </Tiles>
      )}
    </Section>
  );
}

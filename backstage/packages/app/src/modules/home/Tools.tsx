// The Tools page: every door the founder opens, on one page, grouped (crew#684 CP0).
// Founder, 2026-08-30: "i am founder, i am CEO and i am also engineer ... so i need all the
// tools one place ... another page in backstage just pure tools". Pure links: one tile per
// founder-surface entity, its `links:` as buttons, its probe state as the pill the front page
// uses. Nothing here names a tool; the catalogue is the list (LAW 46).
import { Entity } from '@backstage/catalog-model';
import { Content, Link, Page } from '@backstage/core-components';
import {
  ButtonLink,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  Flex,
  Grid,
  Header,
  Text,
} from '@backstage/ui';
import { doorState, entityPath } from './estate';
import { useDoors } from './useDoors';
import { ToolGroup, groupTools, toolsSentence } from './toolGroups';
import { Pill } from './EstateHome';

export const TITLE = 'Tools';

/** One tile per door: state, name, what it is for, and every link it publishes. */
const Tile = ({ entity }: { entity: Entity }) => {
  const s = doorState(entity);
  const links = entity.metadata.links ?? [];
  const title = entity.metadata.title ?? entity.metadata.name;
  return (
    <Card
      data-testid={`tool-${entity.metadata.name}`}
      data-state={s.state}
    >
      <CardHeader>
        <Flex align="center" gap="2">
          <Pill
            state={s.state}
            why={s.why}
            testId={`tool-health-${entity.metadata.name}`}
          />
          <Link to={entityPath(entity)}>{title}</Link>
        </Flex>
      </CardHeader>
      {entity.metadata.description && (
        <CardBody>
          <Text variant="body-small" color="secondary">
            {entity.metadata.description}
          </Text>
        </CardBody>
      )}
      {links.length > 0 && (
        <CardFooter>
          <Flex gap="2">
            {links.map((link, i) => (
              <ButtonLink
                key={link.url}
                href={link.url}
                variant={i === 0 ? 'primary' : 'secondary'}
                size="small"
              >
                {link.title ?? link.url}
              </ButtonLink>
            ))}
          </Flex>
        </CardFooter>
      )}
    </Card>
  );
};

const Group = ({ group }: { group: ToolGroup }) => (
  <section data-testid={`tools-group-${group.name}`}>
    <Flex direction="column" gap="3">
      <Text as="h2" variant="title-small" weight="bold">
        {group.name}{' '}
        <Text as="span" variant="body-small" color="secondary">
          {group.tools.length}
        </Text>
      </Text>
      <Grid.Root columns={{ initial: '1', md: '2', lg: '3' }} gap="3">
        {group.tools.map(e => (
          <Tile key={e.metadata.name} entity={e} />
        ))}
      </Grid.Root>
    </Flex>
  </section>
);

export const Tools = () => {
  const doors = useDoors();
  const groups = doors.state === 'ready' ? groupTools(doors.doors) : [];
  const sentence =
    doors.state === 'loading'
      ? 'Reading the catalogue.'
      : doors.state === 'error'
        ? `The catalogue did not answer, so nothing can be listed. ${doors.error.message}`
        : toolsSentence(groups);

  return (
    <Page themeId="home">
      <Header title={TITLE} description={sentence} />
      <Content>
        {doors.state === 'loading' && (
          <Text
            variant="body-large"
            color="secondary"
            data-testid="tools-loading"
          >
            {sentence}
          </Text>
        )}
        {doors.state === 'error' && (
          <Text
            variant="body-large"
            color="secondary"
            data-testid="tools-error"
          >
            {sentence}
          </Text>
        )}
        {doors.state === 'ready' && (
          <Flex direction="column" gap="6">
            <Text
              variant="body-large"
              color="secondary"
              data-testid="tools-sentence"
            >
              {sentence}
            </Text>
            {groups.map(g => (
              <Group key={g.name} group={g} />
            ))}
          </Flex>
        )}
      </Content>
    </Page>
  );
};

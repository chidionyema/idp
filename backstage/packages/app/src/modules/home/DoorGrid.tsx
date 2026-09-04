// The ten doors as Backstage UI cards, not the home plugin's 64-pixel stamps.
import { Card, CardBody, CardHeader, Flex, Grid, Text } from '@backstage/ui';
import { NAV } from '../nav/EstateNav';
import { DOOR_WHY } from './doorCopy';

export function DoorGrid() {
  return (
    <Grid.Root
      className="estate-home-doors"
      columns={{ initial: '1', sm: '2', lg: '3' }}
      gap="3"
    >
      {NAV.map(({ title, to, icon: Icon }) => (
        <Card key={to} href={to} label={title}>
          <CardHeader>
            <Flex align="center" gap="3">
              <Icon fontSize="small" />
              <Text as="h2" variant="title-small" weight="bold">
                {title}
              </Text>
            </Flex>
          </CardHeader>
          <CardBody>
            <Text variant="body-small" color="secondary">
              {DOOR_WHY[title]}
            </Text>
          </CardBody>
        </Card>
      ))}
    </Grid.Root>
  );
}

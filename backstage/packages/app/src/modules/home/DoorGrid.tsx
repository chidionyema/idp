// The ten doors as Backstage UI cards, not the home plugin's 64-pixel stamps.
import { Card, CardBody, CardHeader, Grid, Text } from '@backstage/ui';
import { NAV } from '../nav/EstateNav';
import { DOOR_WHY } from './doorCopy';

export function DoorGrid() {
  return (
    <Grid.Root columns={{ initial: '1', sm: '2', lg: '3' }} gap="3">
      {NAV.map(({ title, to, icon: Icon }) => (
        <Card key={to} href={to} label={title}>
          <CardHeader>
            <Icon fontSize="small" />
            <Text as="h2" variant="title-small" weight="bold">
              {title}
            </Text>
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

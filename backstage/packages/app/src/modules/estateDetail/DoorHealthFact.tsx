// CP6: the "Is it up?" card on the founder doors (Otto's golden door, the MCP gateway, Otto).
// Before this, each carried only a GitHub link. The card reads the door's own health endpoint
// through the backend proxy (useDoorHealth.ts) and says, in one plain sentence, whether it
// answered -- never a silent green, never a raw HTTP number (LAW 21). Rendered by the estate
// overview only for an entity doorHealthOf() recognises, so every other catalogue page is
// unchanged. Cursor is not here: it has no in-cluster endpoint and wears the vendor card.
import { Entity } from '@backstage/catalog-model';
import { Card, CardContent, Typography } from '@material-ui/core';
import { useDoorHealth } from '../home/useDoorHealth';
import { doorHealthOf, doorSentence } from '../home/doorHealth';
import { StateIcon } from '../home/visuals';
import { State, STATE_WORD } from '../theme/tokens';

/** The verdict's colour word, kept to the estate's six states via two tones: up is good, anything
 * else is not. A raw HTTP number never reaches the person (a number is not a sentence). */
const tone: Record<string, 'inherit' | 'textSecondary' | 'error'> = {
  up: 'inherit',
  reading: 'textSecondary',
  degraded: 'error',
  down: 'error',
};

/** The door verdict's own estate state, so its pill speaks the same six words as everything else:
 * up is good, a failed read is blind (unknown, never a silent green), anything else is the
 * "needs you" state a person has to act on. */
const pillState: Record<string, State> = {
  up: 'good',
  reading: 'blind',
  degraded: 'needs',
  down: 'red',
};

export function DoorHealthFact({ entity }: { entity: Entity }) {
  const door = doorHealthOf(entity.metadata.name);
  const read = useDoorHealth(door);
  if (!door) return null;
  const { verdict, sentence } = doorSentence(door.label, read);
  const state = pillState[verdict] ?? 'blind';
  return (
    <Card variant="outlined" data-testid="door-health-fact">
      <CardContent>
        <Typography variant="overline">Is it up?</Typography>
        <div className="estate-state-pill" data-state={state}>
          <StateIcon state={state} />
          <span className="estate-state-pill-word">{STATE_WORD[state]}</span>
        </div>
        <Typography variant="body2" color={tone[verdict]}>
          {sentence}
        </Typography>
      </CardContent>
    </Card>
  );
}

// CP3: the "Is it up?" card on the three vendor surfaces (Traces/Langfuse, Telemetry/SigNoz,
// Dashboards/Superset). Before this, each card's only fact was a link to the vendor's own login.
// The card reads the vendor's own health endpoint through the backend proxy (useVendor.ts) and
// says, in one plain sentence, whether the door answered -- never a silent green, never a frame
// of the vendor's UI (LAW 21). Rendered by the estate overview only for an entity vendorOf()
// recognises, so every other catalogue page is unchanged.
import { Entity } from '@backstage/catalog-model';
import { Card, CardContent, Typography } from '@material-ui/core';
import { useVendor } from '../home/useVendor';
import { vendorOf, vendorSentence } from '../home/vendor';
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

/** The vendor verdict's own estate state, so its pill speaks the same six words as everything
 * else: up is good, a failed read is blind (unknown, never a silent green), anything else is
 * the "needs you" state a person has to act on. */
const pillState: Record<string, State> = {
  up: 'good',
  reading: 'blind',
  degraded: 'needs',
  down: 'red',
};

export function VendorFact({ entity }: { entity: Entity }) {
  const vendor = vendorOf(entity.metadata.name);
  const read = useVendor(vendor);
  if (!vendor) return null;
  const { verdict, sentence } = vendorSentence(vendor.label, read);
  const state = pillState[verdict] ?? 'blind';
  return (
    <Card variant="outlined" data-testid="vendor-fact">
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

// "Pair my phone" (crew#562, ADR 0009 decision founder-screen-access, path 1 of 3).
//
// Sunshine on the founder's Mac shows a 4-digit PIN in Moonlight on the phone and waits a few
// seconds for someone to type it into Sunshine's own web UI. On 2026-08-28 that someone was a
// session reading Telegram, and two PINs expired before they were entered (crew#562 5457813704).
// Founder: "it times out because in sending agent pin and waiting for them to activate".
//
// This page is that web UI, inside the portal, behind the same login: the PIN goes from the
// founder's thumb to Sunshine's /api/pin over the Backstage proxy (app-config.container.yaml,
// endpoint /sunshine) and the tailnet egress Service (platform/backstage/overlays/oke/
// sunshine-egress.yaml). Nothing in this file names a host, a port or a credential (LAW 46):
// the proxy holds the target and the Authorization header, read from a mounted secret file.
//
// The page is drawn with the estate's shell and Backstage UI, like every other page the
// estate builds (crew#843); it used to be the only surface still built out of Material cards.
import { useState } from 'react';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { Button, Flex, Text, TextField } from '@backstage/ui';
import { EstatePage, Section, Unread, Waiting } from '../shell';

export const TITLE = 'Pair my phone';
export const LEAD =
  'Type the four digits Moonlight shows you, and the phone pairs with the Mac.';

export const PairPhone = () => {
  const fetchApi = useApi(fetchApiRef);
  const discovery = useApi(discoveryApiRef);
  const [pin, setPin] = useState('');
  const [state, setState] = useState<'idle' | 'sending' | 'paired' | 'failed'>(
    'idle',
  );
  const [detail, setDetail] = useState('');

  const submit = async () => {
    setState('sending');
    setDetail('');
    try {
      const base = await discovery.getBaseUrl('proxy');
      const res = await fetchApi.fetch(`${base}/sunshine/api/pin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin: pin.trim(), name: 'founder-phone' }),
      });
      const body = await res.json().catch(() => ({}));
      if (res.ok && body.status !== false) {
        setState('paired');
        setDetail('Paired. Moonlight on your phone now shows the Mac; tap it.');
      } else {
        setState('failed');
        setDetail(
          `Sunshine said no (HTTP ${res.status}). Open Moonlight again for a fresh PIN and retry within its window.`,
        );
      }
    } catch (e) {
      setState('failed');
      setDetail(`Could not reach the Mac over the tailnet: ${String(e)}`);
    }
  };

  return (
    <EstatePage title={TITLE} lead={LEAD}>
      <Section
        title="The PIN"
        blurb="Open Moonlight on the phone and tap the Mac. It shows a four-digit number. The PIN goes straight to the Mac from here; nobody else has to do anything."
      >
        <div className="estate-panel">
          <Flex direction="column" gap="4" align="start">
            <TextField
              label="PIN"
              value={pin}
              inputMode="numeric"
              maxLength={4}
              autoComplete="one-time-code"
              isDisabled={state === 'sending'}
              onChange={value => setPin(value.replace(/\D/g, '').slice(0, 4))}
            />
            <Button
              variant="primary"
              isDisabled={pin.length !== 4 || state === 'sending'}
              isPending={state === 'sending'}
              onPress={submit}
              data-testid="pair"
            >
              Pair
            </Button>
            {state === 'sending' && <Waiting>Pairing the phone…</Waiting>}
            {state === 'paired' && (
              <Text variant="body-medium" data-testid="pair-result">
                {detail}
              </Text>
            )}
            {state === 'failed' && (
              <Unread testId="pair-result">{detail}</Unread>
            )}
          </Flex>
        </div>
      </Section>
    </EstatePage>
  );
};

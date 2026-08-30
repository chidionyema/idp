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
import { useState } from 'react';
import {
  Content,
  ContentHeader,
  Header,
  InfoCard,
  Page,
} from '@backstage/core-components';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { Button, TextField, Typography } from '@material-ui/core';

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
    <Page themeId="home">
      <Header
        title="Pair my phone"
        subtitle="Sunshine on the estate Mac · Moonlight on your phone"
      />
      <Content>
        <ContentHeader title="Type the PIN Moonlight shows you" />
        <InfoCard>
          <Typography paragraph>
            Open Moonlight on the phone, tap the Mac, and it shows a 4-digit
            PIN. Type it here. The PIN reaches the Mac directly; no chat, no
            waiting on anyone.
          </Typography>
          <TextField
            label="PIN"
            value={pin}
            inputProps={{
              inputMode: 'numeric',
              pattern: '[0-9]*',
              maxLength: 4,
              'data-testid': 'pin',
            }}
            onChange={e =>
              setPin(e.target.value.replace(/\D/g, '').slice(0, 4))
            }
            disabled={state === 'sending'}
          />
          <div style={{ marginTop: 16 }}>
            <Button
              variant="contained"
              color="primary"
              disabled={pin.length !== 4 || state === 'sending'}
              onClick={submit}
              data-testid="pair"
            >
              {state === 'sending' ? 'Pairing…' : 'Pair'}
            </Button>
          </div>
          {detail && (
            <Typography
              style={{ marginTop: 16 }}
              color={state === 'failed' ? 'error' : 'textPrimary'}
            >
              {detail}
            </Typography>
          )}
        </InfoCard>
      </Content>
    </Page>
  );
};

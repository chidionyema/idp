// The Investigate page (founder 2026-09-05: "no i would need to be able to ask it fron telegrn
// and backstage also"). HolmesGPT has run in this cluster since 2026-09-05 with its own router
// key, and until this page existed the only thing that could ask it a question was a person with
// a terminal -- an investigator nobody can ask is half a capability.
//
// What happens when the button is pressed: one POST to Holmes' /api/chat carrying {"ask": "..."},
// through the backend proxy (backstage/app-config.yaml, endpoint /holmes). Holmes decides for
// itself which of its tools to run -- it reads pods, events and logs through the Kubernetes API
// and queries Prometheus -- then answers in markdown. Nothing here names a host or a port
// (LAW 46): the proxy holds the target, the fence holds the permission.
//
// What it cannot do, and this is deliberate: Holmes has no shell and no internet access
// (platform/robusta/robusta.yaml declares bash: false and internet: false). It reads the cluster
// and answers; it changes nothing. So this page is safe to leave open.
//
// The same investigator answers on Telegram through the ask_holmes tool on the estate MCP server
// (mcp/plugins/estate_holmes.py). One Holmes, two front doors, no second copy.
import { useState } from 'react';
import { MarkdownContent } from '@backstage/core-components';
import {
  discoveryApiRef,
  fetchApiRef,
  useApi,
} from '@backstage/frontend-plugin-api';
import { Button, Flex, Text, TextField } from '@backstage/ui';
import { EstatePage, Section, Unread, Waiting } from '../shell';

export const TITLE = 'Investigate';
export const LEAD =
  'Ask what is happening in the cluster, in your own words. It reads the pods, the events, the logs and the metrics for itself, and tells you what it found.';

// An empty box teaches nobody what to type. These are the questions worth asking first, and
// pressing one fills the box rather than sending it -- the founder still edits before he asks,
// and one press never spends an investigation he did not mean to spend.
const OPENERS = [
  'What is unhealthy in the cluster right now, and why?',
  'Why is the llm namespace not answering?',
  'Which pods have restarted in the last hour, and what killed them?',
  'Is anything close to running out of memory or CPU?',
];

type Asked =
  | { state: 'idle' }
  | { state: 'asking' }
  | { state: 'answered'; analysis: string; tools: number; seconds: number }
  | { state: 'failed'; detail: string };

export const Investigate = () => {
  const fetchApi = useApi(fetchApiRef);
  const discovery = useApi(discoveryApiRef);
  const [question, setQuestion] = useState('');
  const [asked, setAsked] = useState<Asked>({ state: 'idle' });

  const ask = async () => {
    const text = question.trim();
    if (!text) return;
    setAsked({ state: 'asking' });
    const startedAt = Date.now();
    try {
      const base = await discovery.getBaseUrl('proxy');
      const res = await fetchApi.fetch(`${base}/holmes/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ask: text }),
      });
      const seconds = Math.round((Date.now() - startedAt) / 1000);
      if (!res.ok) {
        setAsked({
          state: 'failed',
          detail: `The investigator refused the question (HTTP ${res.status}). Nothing was changed. Try asking it more narrowly.`,
        });
        return;
      }
      const body = await res.json().catch(() => ({}));
      const analysis = String(body?.analysis ?? '').trim();
      if (!analysis) {
        setAsked({
          state: 'failed',
          detail:
            'The investigator answered without saying anything. That usually means its model lane is out of credit; the router page shows which lanes are live.',
        });
        return;
      }
      const calls = Array.isArray(body?.tool_calls) ? body.tool_calls.length : 0;
      setAsked({ state: 'answered', analysis, tools: calls, seconds });
    } catch (e) {
      setAsked({
        state: 'failed',
        detail: `Could not reach the investigator: ${String(e)}`,
      });
    }
  };

  return (
    <EstatePage title={TITLE} lead={LEAD}>
      <Section
        title="Your question"
        blurb="Plain English. It looks the answer up itself rather than being told where to look, so a question about a symptom works better than one about a file."
      >
        <div className="estate-panel">
          <Flex direction="column" gap="4" align="start">
            <TextField
              label="Ask the investigator"
              value={question}
              isDisabled={asked.state === 'asking'}
              onChange={value => setQuestion(value)}
            />
            <Flex direction="row" gap="2" align="center">
              <Button
                variant="primary"
                isDisabled={!question.trim() || asked.state === 'asking'}
                isPending={asked.state === 'asking'}
                onPress={ask}
                data-testid="investigate-ask"
              >
                Ask
              </Button>
              {asked.state === 'answered' && (
                <Text variant="body-small">
                  {asked.tools === 0
                    ? `Answered in ${asked.seconds}s.`
                    : `Answered in ${asked.seconds}s after reading the cluster ${asked.tools} time${
                        asked.tools === 1 ? '' : 's'
                      }.`}
                </Text>
              )}
            </Flex>
            {asked.state === 'asking' && (
              <Waiting testId="investigate-waiting">
                Reading the cluster. A real investigation runs several queries and
                can take up to a minute.
              </Waiting>
            )}
            {asked.state === 'failed' && (
              <Unread testId="investigate-result">{asked.detail}</Unread>
            )}
          </Flex>
        </div>
      </Section>

      {asked.state === 'idle' && (
        <Section
          title="Questions worth asking first"
          blurb="Press one to put it in the box, then change the wording if you want to."
        >
          <Flex direction="column" gap="2" align="start">
            {OPENERS.map(opener => (
              <Button
                key={opener}
                variant="secondary"
                onPress={() => setQuestion(opener)}
              >
                {opener}
              </Button>
            ))}
          </Flex>
        </Section>
      )}

      {asked.state === 'answered' && (
        <Section
          title="What it found"
          blurb="The investigator read the cluster to answer this. It has no shell and no internet access, and it changed nothing."
        >
          <div className="estate-panel" data-testid="investigate-result">
            <MarkdownContent content={asked.analysis} />
          </div>
        </Section>
      )}
    </EstatePage>
  );
};

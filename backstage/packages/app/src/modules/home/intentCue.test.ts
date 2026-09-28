import { parseIntentResult, cueToReactor, SEVERITY_COLOR } from './intentCue';

const ok = {
  kind: 'intent_result',
  intent: 'ci-status',
  status: 'ok',
  text: 'All green.',
  visual: { cue: 'pulse', target: 'fleet', severity: 'info' },
  ticket: null,
};

test('parses a valid intent_result', () => {
  expect(parseIntentResult(ok)).toEqual(ok);
});

test('rejects non-object and wrong-kind inputs', () => {
  expect(parseIntentResult(null)).toBeNull();
  expect(parseIntentResult('x')).toBeNull();
  expect(parseIntentResult({})).toBeNull();
  expect(parseIntentResult({ ...ok, kind: 'other' })).toBeNull();
});

test('rejects invalid status, cue, target and empty intent', () => {
  expect(parseIntentResult({ ...ok, status: 'nope' })).toBeNull();
  expect(
    parseIntentResult({ ...ok, visual: { ...ok.visual, cue: 'nope' } }),
  ).toBeNull();
  expect(
    parseIntentResult({ ...ok, visual: { ...ok.visual, target: 'node' } }),
  ).toBeNull();
  expect(parseIntentResult({ ...ok, intent: '' })).toBeNull();
});

test('normalizes ticket field', () => {
  const withBadTicket = parseIntentResult({ ...ok, ticket: 42 });
  expect(withBadTicket).toBeTruthy();
  expect(withBadTicket?.ticket).toBeNull();

  const withGoodTicket = parseIntentResult({ ...ok, ticket: 'T-1' });
  expect(withGoodTicket).toBeTruthy();
  expect(withGoodTicket?.ticket).toBe('T-1');
});

test('maps cues to reactor visuals across the contract pairs', () => {
  const errorResult = {
    ...ok,
    status: 'error',
    visual: { cue: 'burn', target: 'fleet', severity: 'danger' },
  };
  const pendingResult = {
    ...ok,
    status: 'pending_confirmation',
    visual: { cue: 'shield_flash', target: 'fleet', severity: 'warn' },
  };
  const cancelledResult = {
    ...ok,
    status: 'cancelled',
    visual: { cue: 'comet_spawn', target: 'fleet', severity: 'info' },
  };

  const okParsed = parseIntentResult(ok);
  const errorParsed = parseIntentResult(errorResult);
  const pendingParsed = parseIntentResult(pendingResult);
  const cancelledParsed = parseIntentResult(cancelledResult);

  expect(okParsed).toBeTruthy();
  expect(errorParsed).toBeTruthy();
  expect(pendingParsed).toBeTruthy();
  expect(cancelledParsed).toBeTruthy();

  const okCue = cueToReactor(okParsed!);
  const errorCue = cueToReactor(errorParsed!);
  const pendingCue = cueToReactor(pendingParsed!);
  const cancelledCue = cueToReactor(cancelledParsed!);

  expect(okCue.kind).toBe('pulse');
  expect(errorCue.kind).toBe('burn');
  expect(pendingCue.kind).toBe('shield');
  expect(cancelledCue.kind).toBe('fire');

  expect(okCue.color).toBe(SEVERITY_COLOR.info);
  expect(errorCue.color).toBe(SEVERITY_COLOR.danger);
  expect(pendingCue.color).toBe(SEVERITY_COLOR.warn);
  expect(cancelledCue.color).toBe(SEVERITY_COLOR.info);
});

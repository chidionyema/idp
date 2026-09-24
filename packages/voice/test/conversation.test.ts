/**
 * Proof, not assertion: the conversation layer is tested, not claimed.
 *
 * These tests lock the three behaviours that make a voice client feel continuous:
 *   1. memory — the last N turns are remembered, oldest-first, never inventing text;
 *   2. cap — the buffer is bounded (a growing prompt is a growing latency);
 *   3. barge-in — an interrupt is a flag that can be set and cleared, not a second voice.
 *
 * Pure functions only: no WebAudio, no microphone, no model. Run with `npm test`.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createConversation, conversationBlock, DEFAULT_TURN_CAP } from '../src/conversation';

test('remembers turns oldest-first and resolves recent()', () => {
  const c = createConversation();
  c.remember('person', 'what is stuck');
  c.remember('agent', 'four are stuck');
  assert.equal(c.history().length, 2);
  assert.equal(c.history()[0].text, 'what is stuck');
  assert.equal(c.recent(1)[0].text, 'four are stuck');
});

test('drops empty turns rather than displacing real ones', () => {
  const c = createConversation(2);
  c.remember('person', '   ');
  c.remember('person', '');
  c.remember('patient', 'real one' as unknown as 'person');
  // The two blank turns must not count against the cap.
  assert.equal(c.history().length, 1);
  assert.equal(c.history()[0].text, 'real one');
});

test('caps the buffer to the configured limit', () => {
  const c = createConversation(3);
  for (let i = 0; i < 10; i++) c.remember('person', `turn ${i}`);
  assert.equal(c.history().length, 3);
  assert.equal(c.history()[0].text, 'turn 7'); // oldest retained
  assert.equal(c.history()[2].text, 'turn 9'); // newest
});

test('recent() filters empty and honours its own limit', () => {
  const c = createConversation();
  c.remember('person', 'a');
  c.remember('agent', '');
  c.remember('person', 'b');
  assert.deepEqual(
    c.recent(1).map((t) => t.text),
    ['b'],
  );
});

test('barge-in is a settable, clearable flag', () => {
  const c = createConversation();
  assert.equal(c.bargedIn, false);
  c.bargeIn();
  assert.equal(c.bargedIn, true);
  c.clearBargeIn();
  assert.equal(c.bargedIn, false);
});

test('reset drops memory and clears the barge-in flag', () => {
  const c = createConversation();
  c.remember('person', 'remember me');
  c.bargeIn();
  c.reset();
  assert.equal(c.history().length, 0);
  assert.equal(c.bargedIn, false);
});

test('conversationBlock matches the server prompt shape', () => {
  const c = createConversation();
  c.remember('person', 'what about that one');
  c.remember('agent', 'the one on the left is pi #bf061c');
  const block = conversationBlock(c);
  assert.match(block, /RECENT CONVERSATION/);
  assert.match(block, /Person: what about that one/);
  assert.match(block, /You: the one on the left is pi #bf061c/);
  // Empty conversation emits an empty block, never a fabricated prompt.
  assert.equal(conversationBlock(createConversation()), '');
});

test('default cap is the server-parity value', () => {
  assert.equal(DEFAULT_TURN_CAP, 6);
});

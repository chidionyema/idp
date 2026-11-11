import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyContactReadiness } from '../scripts/public-readiness.mjs';

test('a configured and valid contact endpoint reports commercial configuration', () => {
  assert.equal(classifyContactReadiness({ acceptingEnquiries: true }), 'configured');
});
test('intentional pre-domain enquiry pause remains a commercial blocker, not a P0 visual failure', () => {
  assert.equal(classifyContactReadiness({ acceptingEnquiries: false }), 'awaiting-inbox-activation');
});
test('missing, malformed, contradictory and absent contact contracts are regressions', () => {
  for (const payload of [null, undefined, {}, [], { acceptingEnquiries: 'true' }, { acceptingEnquiries: 0 }, false]) {
    assert.equal(classifyContactReadiness(payload), 'invalid');
  }
});

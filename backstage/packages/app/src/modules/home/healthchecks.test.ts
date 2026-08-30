import { checksSentence, countBy, notUp, parseChecks } from './healthchecks';

const doc = {
  checks: [
    { name: 'estate-render', status: 'up', tags: 'render' },
    {
      name: 'science-collect',
      status: 'down',
      last_ping: '2026-08-29T20:00:00Z',
    },
    { name: 'login-drill', status: 'grace' },
    { name: 'new-job', status: 'new' },
    { name: 'odd', status: 'exploded' },
  ],
};

describe('healthchecks', () => {
  it('parses the vendor document and counts a state it does not know as unknown', () => {
    const c = parseChecks(doc);
    expect(c.checks.map(x => x.name)).toEqual([
      'estate-render',
      'science-collect',
      'login-drill',
      'new-job',
    ]);
    expect(c.unknown).toBe(1);
    expect(countBy(c)).toEqual({ up: 1, down: 1, grace: 1, new: 1, paused: 0 });
  });

  it('refuses a document without a checks list', () => {
    expect(() => parseChecks({})).toThrow('without a checks list');
  });

  it('says the numbers with their denominator and lists down first', () => {
    const c = parseChecks(doc);
    expect(checksSentence(c)).toBe(
      '1 of 5 up, 1 down, 1 late, 1 never pinged, 1 in a state this page does not know.',
    );
    expect(notUp(c).map(x => x.name)).toEqual([
      'science-collect',
      'login-drill',
      'new-job',
    ]);
  });

  it('is blind, never green, with no checks', () => {
    expect(checksSentence(parseChecks({ checks: [] }))).toBe(
      'No checks are enrolled, so nothing is watched.',
    );
  });
});

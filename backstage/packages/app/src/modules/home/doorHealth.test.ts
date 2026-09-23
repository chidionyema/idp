// CP6: grade the pure founder-door logic -- which catalogue entity is which door, and what one
// read of a door's health endpoint says in words. No proxy, no cluster: the card's rendering is
// thin enough that the sentences are the whole contract (same bar CP3's vendor.test.ts sets).
import { DOOR_HEALTH, doorHealthOf, doorSentence } from './doorHealth';

describe('doorHealthOf (which surface is which door)', () => {
  it('maps the three founder doors the spec names, by their own metadata name', () => {
    expect(doorHealthOf('founder-otto-door')).toEqual(DOOR_HEALTH['founder-otto-door']);
    expect(doorHealthOf('founder-mcp-gateway')).toEqual(DOOR_HEALTH['founder-mcp-gateway']);
    expect(doorHealthOf('founder-otto')).toEqual(DOOR_HEALTH['founder-otto']);
  });

  it('leaves cursor to the vendor card: no in-cluster endpoint means no process read', () => {
    expect(doorHealthOf('founder-cursor')).toBeUndefined();
  });

  it('is undefined for every other catalogue entity, so the card renders nothing', () => {
    expect(doorHealthOf('founder-jobs')).toBeUndefined();
    expect(doorHealthOf('layer-alerts')).toBeUndefined();
    expect(doorHealthOf('')).toBeUndefined();
  });

  it('every door is read-only and lives under the proxy namespace, never a host', () => {
    for (const d of Object.values(DOOR_HEALTH)) {
      expect(d.path.startsWith('/')).toBe(true);
      expect(d.path).not.toMatch(/https?:\/\//);
    }
  });
});

describe('doorSentence (one read -> one plain sentence)', () => {
  it('a 200 is up, because the door its own health endpoint said so', () => {
    expect(doorSentence('The MCP gateway', { state: 'answered', status: 200 })).toEqual({
      verdict: 'up',
      sentence: 'The MCP gateway is up.',
    });
  });

  it('a non-2xx is not green: it answered but is not healthy', () => {
    const s = doorSentence('Otto', { state: 'answered', status: 503 });
    expect(s.verdict).toBe('degraded');
    expect(s.sentence).not.toMatch(/\bup\b/);
  });

  it('a door that could not be reached is down, never a silent green', () => {
    const s = doorSentence('The Otto door', { state: 'unread', error: 'ECONNREFUSED' });
    expect(s.verdict).toBe('down');
    expect(s.sentence).toMatch(/did not answer/);
    // The error detail is machine noise; it never reaches the person.
    expect(s.sentence).not.toMatch(/ECONNREFUSED/);
  });

  it('a loading read is a Reading line, not a verdict', () => {
    const s = doorSentence('Otto', { state: 'loading' });
    expect(s.verdict).toBe('reading');
    expect(s.sentence).toMatch(/Reading/);
  });

  it('never shows a raw HTTP number to a person', () => {
    for (const status of [200, 301, 404, 500]) {
      const s = doorSentence('Otto', { state: 'answered', status });
      expect(s.sentence).not.toMatch(String(status));
    }
  });
});

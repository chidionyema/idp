// CP3: grade the pure vendor-fact logic -- which catalogue entity is which vendor, and what one
// read of a vendor's health endpoint says in words. No proxy, no cluster: the card's rendering is
// thin enough that the sentences are the whole contract (same bar useHealthchecks sets).
import { VENDORS, vendorOf, vendorSentence } from './vendor';

describe('vendorOf (which surface is which vendor)', () => {
  it('maps the three founder surfaces the spec names, by their own metadata name', () => {
    expect(vendorOf('founder-traces')).toEqual(VENDORS.langfuse);
    expect(vendorOf('founder-telemetry')).toEqual(VENDORS.signoz);
    expect(vendorOf('founder-dashboards')).toEqual(VENDORS.superset);
  });

  it('is undefined for every other catalogue entity, so the card renders nothing', () => {
    expect(vendorOf('founder-jobs')).toBeUndefined();
    expect(vendorOf('layer-alerts')).toBeUndefined();
    expect(vendorOf('')).toBeUndefined();
  });

  it('every vendor door is read-only and lives under the proxy namespace, never a host', () => {
    for (const v of Object.values(VENDORS)) {
      expect(v.path.startsWith('/')).toBe(true);
      expect(v.path).not.toMatch(/https?:\/\//);
    }
  });
});

describe('vendorSentence (one read -> one plain sentence)', () => {
  it('a 200 is up, because the vendor its own health endpoint said so', () => {
    expect(vendorSentence('Traces', { state: 'answered', status: 200 })).toEqual({
      verdict: 'up',
      sentence: 'Traces is up.',
    });
  });

  it('a non-2xx is not green: it answered but is not healthy', () => {
    const s = vendorSentence('Telemetry', { state: 'answered', status: 503 });
    expect(s.verdict).toBe('degraded');
    expect(s.sentence).not.toMatch(/\bup\b/);
  });

  it('a vendor that could not be reached is down, never a silent green', () => {
    const s = vendorSentence('Dashboards', { state: 'unread', error: 'ECONNREFUSED' });
    expect(s.verdict).toBe('down');
    expect(s.sentence).toMatch(/did not answer/);
    // The error detail is machine noise; it never reaches the person.
    expect(s.sentence).not.toMatch(/ECONNREFUSED/);
  });

  it('a loading read is a Reading line, not a verdict', () => {
    const s = vendorSentence('Traces', { state: 'loading' });
    expect(s.verdict).toBe('reading');
    expect(s.sentence).toMatch(/Reading/);
  });

  it('never shows a raw HTTP number to a person', () => {
    for (const status of [200, 301, 404, 500]) {
      const s = vendorSentence('Traces', { state: 'answered', status });
      expect(s.sentence).not.toMatch(String(status));
    }
  });
});

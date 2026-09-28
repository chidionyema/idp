import { parseFounder, receiptsSentence, waitingSentence } from './founder';

const data = {
  taken: '2026-08-30T03:00Z',
  waiting: [
    {
      issue: 693,
      url: 'https://github.com/chidionyema/crew/issues/693',
      cp: 'CP1',
      what: 'Founder replies APPROVE',
    },
  ],
  receipts: [
    {
      repo: 'chidionyema/idp',
      number: 918,
      title: 'Ops page',
      url: 'https://github.com/chidionyema/idp/pull/918',
      merged_at: '2026-08-30T03:20:00Z',
      use: 'open the portal, sidebar Ops',
    },
  ],
};

describe('founder data', () => {
  it('parses what estate-founder writes and refuses anything else', () => {
    expect(parseFounder(data).waiting[0].issue).toBe(693);
    expect(() => parseFounder({ taken: 'x' })).toThrow('founder.json');
    expect(() => parseFounder(null)).toThrow('founder.json');
  });

  it('says the numbers', () => {
    expect(waitingSentence(parseFounder(data))).toBe(
      '1 checkpoint waits on you.',
    );
    expect(receiptsSentence(parseFounder(data))).toBe(
      '1 receipt, newest first.',
    );
    expect(waitingSentence({ ...data, waiting: [] })).toBe(
      'Nothing waits on you.',
    );
    expect(receiptsSentence({ ...data, receipts: [] })).toBe(
      'Nothing merged in the window changed what you touch.',
    );
  });
});

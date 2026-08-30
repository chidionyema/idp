// The founder tiles' data (crew#684 CP4): what waits on him and the last receipts, as
// bin/estate-founder writes docs/founder.json on the render schedule. Pure: no fetch here.
export type Waiting = { issue: number; url: string; cp: string; what: string };
export type Receipt = {
  repo: string;
  number: number;
  title: string;
  url: string;
  merged_at: string;
  use: string;
};
export type FounderData = {
  taken: string;
  waiting: Waiting[];
  receipts: Receipt[];
};

/** The path under the estate-state proxy; the same file catalog-render stages. */
export const FOUNDER_JSON = '/estate-state/docs/founder.json';

export const parseFounder = (raw: unknown): FounderData => {
  const o = (raw ?? {}) as Partial<FounderData>;
  if (!Array.isArray(o.waiting) || !Array.isArray(o.receipts) || !o.taken)
    throw new Error('founder.json is not the shape estate-founder writes');
  return { taken: o.taken, waiting: o.waiting, receipts: o.receipts };
};

export const waitingSentence = (d: FounderData) =>
  d.waiting.length === 0
    ? 'Nothing waits on you.'
    : `${d.waiting.length} checkpoint${d.waiting.length === 1 ? '' : 's'} wait${
        d.waiting.length === 1 ? 's' : ''
      } on you.`;

export const receiptsSentence = (d: FounderData) =>
  d.receipts.length === 0
    ? 'Nothing merged in the window changed what you touch.'
    : `${d.receipts.length} receipt${
        d.receipts.length === 1 ? '' : 's'
      }, newest first.`;

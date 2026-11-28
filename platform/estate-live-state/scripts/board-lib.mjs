// The Telegram board's text, built from the same read the terminal makes (watch in watch-lib.mjs),
// so the two cannot disagree about a snapshot. It sends nothing: delivery belongs to the estate's
// one Telegram sender (Otto's pinned card, outbox #8619); this decides only WHAT the card says.
// Two rules the terminal does not need:
//   1. A failed or blind read still produces text. A pinned card that keeps its last good numbers
//      while the feed is down is a green lie, so the card is edited to say BLIND.
//   2. Telegram caps a message at 4096 characters. When the state does not fit, subjects are cut
//      from the end and the card SAYS how many; the parity line is never cut.
import { watch } from "./watch-lib.mjs";

export const TELEGRAM_LIMIT = 4096;

export async function board(opts) {
  const { code, out, err } = await watch(opts);
  if (code !== 0) {
    const why = [...out, ...err].join("\n") || "no reason given";
    return { code, text: `BLIND  estate-live-state\n${why}`.slice(0, TELEGRAM_LIMIT), lines: 0, cut: 0 };
  }
  const parity = out[out.length - 1];
  const head = out[0];
  const subjects = out.slice(1, -1);
  const card = (n) => {
    const cut = subjects.length - n;
    const notice = cut > 0 ? [`TRUNCATED  ${cut} more subject(s) not shown; the parity line below is complete`] : [];
    return [head, ...subjects.slice(0, n), ...notice, parity].join("\n");
  };
  // The most subjects whose finished card, notice included, still fits. Measured, not estimated.
  let n = subjects.length;
  while (n > 0 && card(n).length > TELEGRAM_LIMIT) n--;
  return { code: 0, text: card(n), lines: n, cut: subjects.length - n };
}

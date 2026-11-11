/**
 * The links a session's own ledgers already hold -- the TypeScript twin of
 * platform/estate/governance/plan_links.py::derive_links.
 *
 * pi's extension cannot import Python, so the rule lives twice and the CASES live once:
 * extensions/pi-plan-lock/cases.json holds the cases both copies must agree on, so neither can
 * drift alone. The rule:
 *
 *   instruction = the last NEW intent the intent door recorded under the session
 *                 (the door the work goes through)
 *   prompt      = the newest prompt the prompt ledger recorded under the session
 *                 (the words that started it)
 *
 * Both stay EMPTY when the estate cannot prove them: an empty link is a gap the plan-link door
 * reports, not a value invented here.
 */

export type DerivationRows = {
  intents?: Array<Record<string, unknown>>;
  prompts?: Array<Record<string, unknown>>;
};

export type DerivedLinks = {
  instruction: string;
  prompt: string;
};

/** The instruction: the last NEW intent name for this session, in first-seen order. */
export function deriveInstruction(session: string, intents: Array<Record<string, unknown>>): string {
  const seen: string[] = [];
  for (const row of intents ?? []) {
    if (String(row?.session ?? "") !== session) continue;
    const name = String(row?.intent ?? "");
    if (name && !seen.includes(name)) seen.push(name);
  }
  return seen.length ? seen[seen.length - 1] : "";
}

/** The founder prompt: the newest prompt recorded under this session. */
export function derivePrompt(session: string, prompts: Array<Record<string, unknown>>): string {
  let prompt = "";
  for (const row of prompts ?? []) {
    if (String(row?.session ?? "") !== session) continue;
    const id = String(row?.id ?? "");
    if (id) prompt = id;
  }
  return prompt;
}

/** Both links, from both ledgers. */
export function deriveLinks(session: string, rows: DerivationRows): DerivedLinks {
  return {
    instruction: deriveInstruction(session, rows.intents ?? []),
    prompt: derivePrompt(session, rows.prompts ?? []),
  };
}

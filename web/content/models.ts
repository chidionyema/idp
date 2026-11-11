// The model roster shown by the cost calculator, the routing playground and the
// playground endpoint. One list, so a price can never drift between the three.
//
// Every rate is a published list price per 1M tokens, read from the provider's own
// rate card on the date below. Nothing here is an estimate and nothing here is a
// number we measured ourselves. A model that a provider has retired or deprecated
// does not belong on this list: a customer who picks one from a consultancy site
// and gets a 410 from the API has been misled.
export interface Model {
  key: string;
  label: string;
  provider: string;
  inputPer1M: number;
  outputPer1M: number;
  color: string;
  bestFor: string;
  speed: string;
}

/** When these rates were last read from the providers' published rate cards. */
export const pricingChecked = "11 November 2026";

export const models: Model[] = [
  {
    key: "gpt-6-luna",
    label: "GPT-6 Luna",
    provider: "OpenAI",
    inputPer1M: 0.10,
    outputPer1M: 0.50,
    color: "#1A56DB",
    bestFor: "Classification and high-volume work",
    speed: "Fast",
  },
  {
    key: "claude-haiku-5-5",
    label: "Claude Haiku 5.5",
    provider: "Anthropic",
    inputPer1M: 0.10,
    outputPer1M: 0.50,
    color: "#059669",
    bestFor: "Short reasoning at volume",
    speed: "Fast",
  },
  {
    key: "gemini-3.8-flash",
    label: "Gemini 3.8 Flash",
    provider: "Google",
    inputPer1M: 0.75,
    outputPer1M: 3.75,
    color: "#D97706",
    bestFor: "Long context and agentic runs",
    speed: "Fast",
  },
  {
    key: "gpt-6.1-terra",
    label: "GPT-6.1 Terra",
    provider: "OpenAI",
    inputPer1M: 1.00,
    outputPer1M: 5.00,
    color: "#1A56DB",
    bestFor: "General work at mid cost",
    speed: "Medium",
  },
  {
    key: "claude-sonnet-5-5",
    label: "Claude Sonnet 5.5",
    provider: "Anthropic",
    inputPer1M: 2.00,
    outputPer1M: 10.00,
    color: "#059669",
    bestFor: "Frontier reasoning and coding",
    speed: "Medium",
  },
];

export function modelByKey(key: string): Model | undefined {
  return models.find((m) => m.key === key);
}

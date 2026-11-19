export interface ProviderRateCard {
  modelSlug: string;
  provider: string;
  displayName: string;
  inputPer1MUsd: number;
  cachedInputPer1MUsd: number;
  outputPer1MUsd: number;
  reasoningPer1MUsd: number;
  currency: 'USD';
  sourceNote: string;
}

/**
 * Deterministic per-1M-token rate cards for every supported model provider.
 * Used for exact PennyD actual spend vs. unrouted "Without PennyD" counterfactual math.
 */
export const PROVIDER_RATE_CARDS: Record<string, ProviderRateCard> = {
  'deepseek-chat': {
    modelSlug: 'deepseek-chat',
    provider: 'DeepSeek',
    displayName: 'DeepSeek V3 / Chat',
    inputPer1MUsd: 0.28,
    cachedInputPer1MUsd: 0.028,
    outputPer1MUsd: 0.42,
    reasoningPer1MUsd: 0.42,
    currency: 'USD',
    sourceNote: 'DeepSeek API standard + context cache hit pricing',
  },
  'deepseek-reasoner': {
    modelSlug: 'deepseek-reasoner',
    provider: 'DeepSeek',
    displayName: 'DeepSeek R1 Reasoner',
    inputPer1MUsd: 0.55,
    cachedInputPer1MUsd: 0.14,
    outputPer1MUsd: 2.19,
    reasoningPer1MUsd: 2.19,
    currency: 'USD',
    sourceNote: 'DeepSeek Reasoner input/cache/reasoning-output schedule',
  },
  'claude-sonnet-4': {
    modelSlug: 'claude-sonnet-4',
    provider: 'Anthropic',
    displayName: 'Claude Sonnet 4',
    inputPer1MUsd: 3.0,
    cachedInputPer1MUsd: 0.3,
    outputPer1MUsd: 15.0,
    reasoningPer1MUsd: 15.0,
    currency: 'USD',
    sourceNote: 'Anthropic Sonnet standard + prompt caching (90% read discount)',
  },
  'claude-opus-4-1': {
    modelSlug: 'claude-opus-4-1',
    provider: 'Anthropic',
    displayName: 'Claude Opus 4.1 (Unrouted Baseline)',
    inputPer1MUsd: 15.0,
    cachedInputPer1MUsd: 1.5,
    outputPer1MUsd: 75.0,
    reasoningPer1MUsd: 75.0,
    currency: 'USD',
    sourceNote: 'Flagship unrouted reasoning baseline reference',
  },
  'gemini-2.5-flash': {
    modelSlug: 'gemini-2.5-flash',
    provider: 'Google',
    displayName: 'Gemini 2.5 Flash',
    inputPer1MUsd: 0.3,
    cachedInputPer1MUsd: 0.075,
    outputPer1MUsd: 2.5,
    reasoningPer1MUsd: 2.5,
    currency: 'USD',
    sourceNote: 'Google Gemini 2.5 Flash standard + context caching',
  },
  'gpt-4o-mini': {
    modelSlug: 'gpt-4o-mini',
    provider: 'OpenAI',
    displayName: 'GPT-4o Mini',
    inputPer1MUsd: 0.15,
    cachedInputPer1MUsd: 0.075,
    outputPer1MUsd: 0.6,
    reasoningPer1MUsd: 0.6,
    currency: 'USD',
    sourceNote: 'OpenAI GPT-4o Mini standard + cached input',
  },
  'gpt-4o': {
    modelSlug: 'gpt-4o',
    provider: 'OpenAI',
    displayName: 'GPT-4o (Unrouted Baseline)',
    inputPer1MUsd: 2.5,
    cachedInputPer1MUsd: 1.25,
    outputPer1MUsd: 10.0,
    reasoningPer1MUsd: 10.0,
    currency: 'USD',
    sourceNote: 'OpenAI flagship direct uncached baseline reference',
  },
};

export interface TokenBreakdownInput {
  modelSlug: string;
  baselineModelSlug: string;
  uncachedInputTokens: number;
  cachedInputTokens: number;
  outputTokens: number;
  reasoningTokens: number;
  contextTrimSavedTokens: number;
}

export interface TokenEconomicsResult {
  modelSlug: string;
  baselineModelSlug: string;
  uncachedInputTokens: number;
  cachedInputTokens: number;
  outputTokens: number;
  reasoningTokens: number;
  totalExecutedTokens: number;
  tokensSavedByPennyD: number;
  actualInputCostUsd: number;
  actualCacheCostUsd: number;
  actualOutputCostUsd: number;
  actualReasoningCostUsd: number;
  actualTotalCostUsd: number;
  withoutPennydCostUsd: number;
  usdSaved: number;
  savingsPct: number;
  formulaSummary: string;
}

function roundMicroUsd(val: number): number {
  return Number(val.toFixed(6));
}

export function getRateCard(modelSlug: string): ProviderRateCard {
  return PROVIDER_RATE_CARDS[modelSlug] ?? PROVIDER_RATE_CARDS['deepseek-chat'];
}

/**
 * Computes exact micro-dollar cost for executed tokens and counterfactual
 * "Without PennyD" spend (no prompt cache hit, no context trim, and baseline model pricing).
 */
export function calculateTokenEconomics(input: TokenBreakdownInput): TokenEconomicsResult {
  const rate = getRateCard(input.modelSlug);
  const baseline = getRateCard(input.baselineModelSlug);

  const uncachedIn = Math.max(0, Math.round(input.uncachedInputTokens));
  const cachedIn = Math.max(0, Math.round(input.cachedInputTokens));
  const out = Math.max(0, Math.round(input.outputTokens));
  const reasoning = Math.max(0, Math.round(input.reasoningTokens));
  const trimSaved = Math.max(0, Math.round(input.contextTrimSavedTokens));

  const actualInputCostUsd = roundMicroUsd((uncachedIn * rate.inputPer1MUsd) / 1_000_000);
  const actualCacheCostUsd = roundMicroUsd((cachedIn * rate.cachedInputPer1MUsd) / 1_000_000);
  const actualOutputCostUsd = roundMicroUsd((out * rate.outputPer1MUsd) / 1_000_000);
  const actualReasoningCostUsd = roundMicroUsd((reasoning * rate.reasoningPer1MUsd) / 1_000_000);
  const actualTotalCostUsd = roundMicroUsd(
    actualInputCostUsd + actualCacheCostUsd + actualOutputCostUsd + actualReasoningCostUsd
  );

  // Without PennyD: full uncached input (including trimmed context) + full output+reasoning on baseline model
  const counterfactualInputTokens = uncachedIn + cachedIn + trimSaved;
  const counterfactualOutputTokens = out + reasoning;
  const withoutPennydCostUsd = roundMicroUsd(
    (counterfactualInputTokens * baseline.inputPer1MUsd +
      counterfactualOutputTokens * baseline.outputPer1MUsd) /
      1_000_000
  );

  const usdSaved = roundMicroUsd(withoutPennydCostUsd - actualTotalCostUsd);
  const savingsPct =
    withoutPennydCostUsd > 0 ? Number(((usdSaved / withoutPennydCostUsd) * 100).toFixed(2)) : 0;

  // Token savings = context tokens pruned before dispatch + cached tokens avoiding full recomputation weight
  const tokensSavedByPennyD = trimSaved + cachedIn;
  const totalExecutedTokens = uncachedIn + cachedIn + out + reasoning;

  const formulaSummary =
    `Actual = (${uncachedIn}×$${rate.inputPer1MUsd} + ${cachedIn}×$${rate.cachedInputPer1MUsd} + ${out}×$${rate.outputPer1MUsd} + ${reasoning}×$${rate.reasoningPer1MUsd}) / 1M = $${actualTotalCostUsd.toFixed(6)} | ` +
    `Without PennyD (${baseline.modelSlug}) = (${counterfactualInputTokens}×$${baseline.inputPer1MUsd} + ${counterfactualOutputTokens}×$${baseline.outputPer1MUsd}) / 1M = $${withoutPennydCostUsd.toFixed(6)}`;

  return {
    modelSlug: rate.modelSlug,
    baselineModelSlug: baseline.modelSlug,
    uncachedInputTokens: uncachedIn,
    cachedInputTokens: cachedIn,
    outputTokens: out,
    reasoningTokens: reasoning,
    totalExecutedTokens,
    tokensSavedByPennyD,
    actualInputCostUsd,
    actualCacheCostUsd,
    actualOutputCostUsd,
    actualReasoningCostUsd,
    actualTotalCostUsd,
    withoutPennydCostUsd,
    usdSaved,
    savingsPct,
    formulaSummary,
  };
}

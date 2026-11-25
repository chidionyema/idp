// The role pool the Zone B edge serves, derived from the estate's recorded lane truth.
//
// Nothing here is invented. Every field is traceable to a line in this repository, so a
// drift is checkable rather than a matter of opinion:
//
//   MiniMax   llm/config.yaml: `openai/MiniMax-M3`, api_base https://api.minimax.io/v1,
//             max_tokens 8192, input_cost_per_token 0.0000003, output_cost_per_token
//             0.0000012, model_info.max_input_tokens 512000.
//   DeepSeek  llm/config.yaml: `deepseek/deepseek-chat`, max_tokens 8192,
//             "DeepSeek V3 pricing: $0.14/M input, $0.28/M output", max_input_tokens 65536.
//   Gemini    llm/config.yaml: `gemini/gemini-3.5-flash`, "measured answering HTTP 200 with
//             a real completion", no cost fields ("the day Gemini is billed again"), and the
//             recorded rule that "Gemini goes last everywhere and heads nothing".
//
// Liveness was measured on 2026-11-25 with the keys the estate holds, and is recorded here
// rather than assumed: MiniMax answers 402 `insufficient_balance_error` ("Token Plan usage
// limit reached"), DeepSeek 401 `authentication_error`, OpenRouter 402, Moonshot 401;
// Gemini's key lists 65 models (HTTP 200) and is the only live lane. The lanes are NOT
// disabled for that: the router fails over on 401/402/403 and opens a circuit on the lane
// it sees fail, so a top-up heals without a code change, and a dead lane costs one attempt
// rather than a retry forever.
//
// The pool is repo truth, not release env: seeding from the same table on every release is
// what lets a key set out-of-band (the Cloudflare dashboard) start serving with no code
// change — the release does not need to hold the vendor key to advertise the lane.

// The Worker resolves `apiKeySecretName` as its OWN env binding; the release step uploads
// it from the estate's `SEED_*` name when it holds one. One mapping, never two literals.
export const VENDOR_BINDINGS = [
  { binding: "MINIMAX_API_KEY", seed: "SEED_MINIMAX_API_KEY" },
  { binding: "DEEPSEEK_API_KEY", seed: "SEED_DEEPSEEK_API_KEY" },
  { binding: "GEMINI_API_KEY", seed: "SEED_GEMINI_API_KEY" },
];

// `supportsTools` stays false on every lane: the recorded lane truth never says these
// lanes may be used for tool calls, and a wrong `true` routes a tool call to a vendor that
// ignores it. Raising it is a measurement, not an edit.
const CANDIDATES = [
  {
    id: "minimax-m3",
    vendor: "minimax",
    lane: "edge-direct",
    baseUrl: "https://api.minimax.io/v1/chat/completions",
    apiKeySecretName: "MINIMAX_API_KEY",
    upstreamModel: "MiniMax-M3",
    maxContextTokens: 512000,
    maxOutputTokens: 8192,
    supportsTools: false,
    priority: 1,
    costPer1kInputUsd: 0.0003,
    costPer1kOutputUsd: 0.0012,
    enabled: true,
  },
  {
    id: "deepseek-chat",
    vendor: "deepseek",
    lane: "edge-direct",
    baseUrl: "https://api.deepseek.com/chat/completions",
    apiKeySecretName: "DEEPSEEK_API_KEY",
    upstreamModel: "deepseek-chat",
    maxContextTokens: 65536,
    maxOutputTokens: 8192,
    supportsTools: false,
    priority: 2,
    costPer1kInputUsd: 0.00014,
    costPer1kOutputUsd: 0.00028,
    enabled: true,
  },
  {
    // Last by the recorded rule, and the only lane measured live on 2026-11-25.
    id: "gemini-3.5-flash",
    vendor: "gemini",
    lane: "edge-direct",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    apiKeySecretName: "GEMINI_API_KEY",
    upstreamModel: "gemini-3.5-flash",
    // The lane's recorded row carries no context ceiling, so this pool uses the smallest
    // ceiling it already trusts (deepseek's 65536): a prompt too large for Google is then
    // refused here instead of travelling to the vendor as a 400.
    maxContextTokens: 65536,
    maxOutputTokens: 8192,
    supportsTools: false,
    priority: 3,
    // Free tier: llm/config.yaml carries no cost fields for this lane on purpose.
    costPer1kInputUsd: 0,
    costPer1kOutputUsd: 0,
    enabled: true,
  },
];

// wrangler.toml sets DEFAULT_OUTPUT_FLOOR = "2048"; the pool's floor must not be lower.
export const MIN_OUTPUT_FLOOR = 2048;

export function vendorSecrets(env) {
  const secrets = {};
  for (const { binding, seed } of VENDOR_BINDINGS) {
    if (env[seed]) secrets[binding] = env[seed];
  }
  return secrets;
}

/**
 * The admin-API payload, from the repo's own table. `enabled` is the estate's decision,
 * not the release's: a lane is switched off here with its measurement, and liveness at
 * call time is the router's job (failover + circuit), not a guess made before the deploy.
 */
export function rolePool() {
  const candidates = CANDIDATES.map((c) => ({ ...c }));
  if (!candidates.some((c) => c.enabled)) return { roles: {} };
  return {
    roles: {
      "role:coder": { role: "role:coder", minOutputFloor: MIN_OUTPUT_FLOOR, candidates },
    },
  };
}

/**
 * PUT /admin/v1/roles. Idempotent by contract (`roles_v1` is replaced wholesale), which is
 * why the caller may retry it while a freshly deployed version propagates. A refusal is
 * named with the provider's own body — never swallowed, never retried into a pass.
 */
export async function seedRolePool(baseUrl, adminKey, payload, fetchImpl = fetch) {
  const roles = Object.keys(payload?.roles ?? {});
  if (!roles.length) return { configured: 0, status: 0, skipped: "no enabled candidate" };
  const res = await fetchImpl(baseUrl + "/admin/v1/roles", {
    method: "PUT",
    headers: { authorization: "Bearer " + adminKey, "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await res.text();
  if (!res.ok) throw new Error(`role seed refused ${res.status}: ${body.slice(0, 200)}`);
  return { configured: roles.length, status: res.status };
}

/**
 * Read the live pool back. The receipt must prove what the router holds, not what the
 * script sent: a PUT that answered 200 and a pool the deployment cannot see are two
 * different facts, and this is the measurement that tells them apart.
 */
export async function liveRoles(baseUrl, adminKey, fetchImpl = fetch) {
  const res = await fetchImpl(baseUrl + "/admin/v1/roles", {
    headers: { authorization: "Bearer " + adminKey },
  });
  if (!res.ok) throw new Error(`role read refused ${res.status}`);
  const data = await res.json();
  return Object.keys(data?.roles ?? {});
}

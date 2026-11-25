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
//
// Both chat-completions paths were measured 2026-11-25 (unauthenticated, so no key was
// printed): POST https://api.minimax.io/v1/chat/completions -> 401 authorized_error;
// POST https://api.deepseek.com/chat/completions -> 401 "Authentication Fails" — the
// path exists and demands a bearer.
//
// A candidate is only offered when the Worker will actually hold its key. A pool naming a
// vendor the edge cannot authenticate to is a 502 on every call, and an empty pool is the
// `unknown_role` refusal measured on run 45675424976 while /health said 200.

// The Worker resolves `apiKeySecretName` as its OWN env binding; the release step holds
// the value under the estate's `SEED_*` name. One mapping, never two literals.
export const VENDOR_BINDINGS = [
  { binding: "MINIMAX_API_KEY", seed: "SEED_MINIMAX_API_KEY" },
  { binding: "DEEPSEEK_API_KEY", seed: "SEED_DEEPSEEK_API_KEY" },
];

// `supportsTools` stays false on both lanes: the recorded lane truth never says either
// vendor may be used for tool calls, and a wrong `true` routes a tool call to a vendor
// that ignores it. Raising it is a measurement, not an edit.
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
 * The admin-API payload. Candidates whose key the Worker will not hold are dropped, so a
 * role is never advertised without a lane that can serve it. No key, no role: an empty
 * `roles` object is what the caller must see rather than a pool of guarantees.
 */
export function rolePool(env) {
  const held = new Set(Object.keys(vendorSecrets(env)));
  const candidates = CANDIDATES
    .filter((c) => held.has(c.apiKeySecretName))
    .map((c) => ({ ...c }));
  if (!candidates.length) return { roles: {} };
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
  if (!roles.length) return { configured: 0, status: 0, skipped: "no vendor key held" };
  const res = await fetchImpl(baseUrl + "/admin/v1/roles", {
    method: "PUT",
    headers: { authorization: "Bearer " + adminKey, "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await res.text();
  if (!res.ok) throw new Error(`role seed refused ${res.status}: ${body.slice(0, 200)}`);
  return { configured: roles.length, status: res.status };
}

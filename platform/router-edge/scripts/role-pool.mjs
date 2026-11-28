// The role pool the Zone B edge serves, derived from the estate's recorded lane truth.
//
// Nothing here is invented. Every field is traceable to a line in this repository, so a
// drift is checkable rather than a matter of opinion:
//
//   MiniMax   llm/config.yaml: `openai/MiniMax-M3`, api_base https://api.minimax.io/v1,
//             max_tokens 8192, input_cost_per_token 0.0000003, output_cost_per_token
//             0.0000012, model_info.max_input_tokens 512000.
//   DeepSeek  api-docs.deepseek.com/quick_start/pricing (read 2026-11-28): `deepseek-flash` and
//             `deepseek-v4-pro`, 1M context. llm/config.yaml still names the retired
//             `deepseek-chat`; that file is not this pool's source for DeepSeek any more.
//   Gemini    llm/config.yaml: `gemini/gemini-3.5-flash`, "measured answering HTTP 200 with
//             a real completion", no cost fields ("the day Gemini is billed again"), and the
//             recorded rule that "Gemini goes last everywhere and heads nothing".
//
// Liveness is not recorded in this file, because a recorded liveness is a claim that goes
// stale (this paragraph said MiniMax was dead on 2026-11-25; the edge's own binding served it
// on 2026-11-28). The release measures every lane through the Worker and writes the verdict to
// the receipt (`lanes`, `dead_lanes`). Lanes are NOT disabled for being dead: the router fails
// over on 401/402/403 and opens a circuit on the lane it sees fail, so a fixed key heals
// without a code change, and a dead lane costs one attempt rather than a retry forever.
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
  // DeepSeek's current API models, read from https://api-docs.deepseek.com/quick_start/pricing
  // on 2026-11-28: `deepseek-flash` (DeepSeek-V4.1-Flash-1017) and `deepseek-v4-pro`
  // (DeepSeek-V4-Pro-0813), 1M context, peak-rate USD per 1M tokens: flash 0.30 in / 1.20 out,
  // pro 1.32 in / 3.96 out. `deepseek-chat` (V3.x) is no longer in that table, so the lane that
  // still named it was calling a retired id; it is replaced, not kept beside the new ones.
  {
    id: "deepseek-flash",
    vendor: "deepseek",
    lane: "edge-direct",
    baseUrl: "https://api.deepseek.com/chat/completions",
    apiKeySecretName: "DEEPSEEK_API_KEY",
    upstreamModel: "deepseek-flash",
    maxContextTokens: 1000000,
    maxOutputTokens: 8192,
    supportsTools: false,
    priority: 2,
    costPer1kInputUsd: 0.0003,
    costPer1kOutputUsd: 0.0012,
    enabled: true,
  },
  {
    id: "deepseek-v4-pro",
    vendor: "deepseek",
    lane: "edge-direct",
    baseUrl: "https://api.deepseek.com/chat/completions",
    apiKeySecretName: "DEEPSEEK_API_KEY",
    upstreamModel: "deepseek-v4-pro",
    maxContextTokens: 1000000,
    maxOutputTokens: 8192,
    supportsTools: false,
    priority: 3,
    costPer1kInputUsd: 0.00132,
    costPer1kOutputUsd: 0.00396,
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
    priority: 4,
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

// A lane that nobody has called is a claim, not a lane. `role:coder` fails over, so it
// answers 200 while lanes are dead (measured 2026-11-28: DeepSeek 401 behind a 200). Each
// enabled lane therefore also gets a one-candidate role named by its own id, `role:<lane>`.
// That pinned role has two jobs and one definition: a client names exactly this lane
// (`model: "deepseek-flash"`, which is what Codex's model picker sends), and the release calls
// every pinned role through the Worker, which holds the vendor keys. A retired model id, a
// revoked key or an empty wallet is then a named lane in the receipt on the release that
// introduced it, not a silent failover. Adding a lane to CANDIDATES is the whole change.
export function laneRoleName(laneId) {
  return "role:" + laneId;
}

export function isPinnedRole(name, role) {
  return role?.candidates?.length === 1 && laneRoleName(role.candidates[0].id) === name;
}

export function releasePool() {
  const pool = rolePool();
  const roles = { ...pool.roles };
  for (const c of CANDIDATES.filter((x) => x.enabled)) {
    const name = laneRoleName(c.id);
    if (roles[name]) throw new Error(`lane id ${c.id} collides with the pool role ${name}`);
    roles[name] = { role: name, minOutputFloor: MIN_OUTPUT_FLOOR, candidates: [{ ...c, priority: 1 }] };
  }
  return { roles };
}

/**
 * Call every enabled lane once through its own pinned role. Only a 200 with assistant text
 * from the lane that was asked for counts as serving; anything else names the lane and the
 * status. Unknown is dead: a lane that cannot be judged is not reported live.
 */
export async function probeLanes(baseUrl, clientKey, pool = releasePool(), fetchImpl = fetch) {
  const lanes = [];
  for (const [name, role] of Object.entries(pool.roles).filter(([n, r]) => isPinnedRole(n, r))) {
    const id = role.candidates[0].id;
    const row = { id, ok: false, status: 0, backend: null, error: null };
    try {
      const res = await fetchImpl(baseUrl + "/v1/chat/completions", {
        method: "POST",
        headers: { "content-type": "application/json", authorization: "Bearer " + clientKey },
        body: JSON.stringify({ model: name, max_tokens: 16, messages: [{ role: "user", content: "Reply with: OK" }] }),
      });
      const body = await res.text();
      row.status = res.status;
      row.backend = res.headers.get("x-meridian-backend");
      let text = "";
      try { text = JSON.parse(body)?.choices?.[0]?.message?.content ?? ""; } catch { /* not JSON */ }
      row.ok = res.status === 200 && row.backend === id && String(text).length > 0;
      if (!row.ok) row.error = body.replace(/\s+/g, " ").slice(0, 200);
    } catch (e) {
      row.error = String(e?.message ?? e).slice(0, 160);
    }
    lanes.push(row);
  }
  return lanes;
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

/**
 * The Codex surface: `GET /v1/models` must list every enabled lane by id, and `POST
 * /v1/responses` (what Codex 0.169 speaks; it refuses wire_api "chat") must answer with
 * assistant text from the lane that was named, as a plain body and as SSE ending in
 * response.completed. Unknown is not ok.
 */
export async function probeCodexSurface(baseUrl, clientKey, laneId, pool = releasePool(), fetchImpl = fetch) {
  const out = { ok: false, models_missing: [], responses_status: 0, stream_completed: false, error: null };
  const headers = { "content-type": "application/json", authorization: "Bearer " + clientKey };
  try {
    const m = await fetchImpl(baseUrl + "/v1/models", { headers });
    const listed = new Set(((await m.json())?.data ?? []).map((x) => x.id));
    out.models_missing = Object.keys(pool.roles).map((n) => n.slice(5)).filter((id) => !listed.has(id));
    const ask = (stream) => fetchImpl(baseUrl + "/v1/responses", {
      method: "POST", headers,
      body: JSON.stringify({ model: laneId, input: "Reply with: OK", max_output_tokens: 16, stream }),
    });
    const r = await ask(false);
    out.responses_status = r.status;
    const rb = await r.text();
    const text = JSON.parse(rb)?.output?.[0]?.content?.[0]?.text ?? "";
    const s = await ask(true);
    const sb = await s.text();
    out.stream_completed = s.status === 200 && /event: response\.completed/.test(sb);
    out.ok = m.status === 200 && !out.models_missing.length && r.status === 200 && String(text).length > 0 && out.stream_completed;
    if (!out.ok) out.error = rb.replace(/\s+/g, " ").slice(0, 200);
  } catch (e) {
    out.error = String(e?.message ?? e).slice(0, 160);
  }
  return out;
}

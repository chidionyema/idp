// Off-host founder seal (I-8107 / LAW_PORTABLE_ES256_VAULT).
//
// The estate's seal is an X-Idp-Auth trailer: base64 Ed25519 over
//   <utc iso>\n<head sha>\n<reason>\n<newline-joined paths>
// verified by bin/idp-auth-verify against docs/keys/founder.pub.
//
// Until now the only thing that could produce one was ~/.idp/founder.key on one laptop, signed
// by an openssl CLI that does not work under LibreSSL -- so a guarded path could not be changed
// from anywhere. This handler moves the signing to the Worker: the key is a Cloudflare secret,
// the caller proves authority with a bearer token, and the output is the exact trailer the
// existing verifier already accepts. Nothing on the estate changes except where the private key
// lives.

const TRAILER_REASON_LIMIT = 200;

/** The exact bytes bin/idp-auth signs. Kept identical on purpose: a signature is only useful
 *  if the verifier reconstructs the same string. */
export function sealPayload({ ts, head, reason, paths }) {
  // Shell signer and verifier both remove trailing newlines via command substitution.
  return `${ts}\n${head}\n${reason}\n${paths.join("\n")}`;
}

export function utf8(s) {
  return new TextEncoder().encode(s);
}

export function b64(bytes) {
  let out = "";
  const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 1) out += String.fromCharCode(view[i]);
  return btoa(out);
}

function pemToDer(pem) {
  const body = pem
    .replace(/-----BEGIN [^-]+-----/g, "")
    .replace(/-----END [^-]+-----/g, "")
    .replace(/\s+/g, "");
  const raw = atob(body);
  const der = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) der[i] = raw.charCodeAt(i);
  return der;
}

export async function signSeal(env, { reason, paths, head }, now = () => new Date()) {
  if (!env || !env.FOUNDER_SEAL_KEY_PEM) {
    return { ok: false, status: 501, error: "seal_key_absent" };
  }
  if (!reason || typeof reason !== "string" || reason.length > TRAILER_REASON_LIMIT) {
    return { ok: false, status: 400, error: "reason_required" };
  }
  if (!Array.isArray(paths) || paths.length === 0 || paths.some((p) => typeof p !== "string")) {
    return { ok: false, status: 400, error: "paths_required" };
  }
  if (!/^([0-9a-f]{40}|no-head)$/.test(head || "")) {
    return { ok: false, status: 400, error: "head_must_be_40_hex_or_no-head" };
  }

  const key = await crypto.subtle.importKey(
    "pkcs8",
    pemToDer(env.FOUNDER_SEAL_KEY_PEM),
    { name: "Ed25519" },
    false,
    ["sign"],
  );
  const ts = now().toISOString().replace(/\.\d{3}Z$/, "Z");
  const payload = sealPayload({ ts, head, reason, paths });
  const sig = await crypto.subtle.sign({ name: "Ed25519" }, key, utf8(payload));
  const trailer = [
    `X-Idp-Auth: ${b64(sig)}`,
    `X-Idp-Auth-Reason: ${reason}`,
    `X-Idp-Auth-Timestamp: ${ts}`,
    `X-Idp-Auth-Paths: ${paths.join(",")}`,
  ].join("\n");
  return { ok: true, status: 200, trailer, ts, payload };
}

const CORS = {
  "Access-Control-Allow-Origin": "https://genesis-founder-surface.pages.dev",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

function json(status, body) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}

/** POST /seal  { reason, paths[], head }  with Authorization: Bearer <FOUNDER_SEAL_TOKEN> */
export async function handleSeal(request, env, now) {
  const auth = request.headers.get("Authorization") || "";
  const expected = env && env.FOUNDER_SEAL_TOKEN;
  if (!expected || auth !== `Bearer ${expected}`) {
    return json(401, { error: "unauthorized" });
  }
  let body;
  try {
    body = await request.json();
  } catch {
    return json(400, { error: "body_must_be_json" });
  }
  const result = await signSeal(
    env,
    { reason: body && body.reason, paths: body && body.paths, head: body && body.head },
    now,
  );
  if (!result.ok) return json(result.status, { error: result.error });
  return json(200, { trailer: result.trailer, timestamp: result.ts });
}

export const SEAL_OPTIONS = async () => new Response(null, { status: 204, headers: CORS });

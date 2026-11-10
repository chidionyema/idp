// The brain state door: what the estate KNOWS, at the edge, with no cluster behind it.
//
// THE DEFECT THIS RETIRES. `genesis-founder-surface.pages.dev/api/brain/state` answered
//
//   { "status": "cloud-read-only", "authority": "github-canonical" }
//
// which is honest and useless: a founder surface that can read the estate's state and cannot
// record anything into it is a mirror, and every instruction the founder speaks at a dead
// cluster lands in a void. The estate's own words for that failure are "the founder repeats
// himself" (AGENTS.md section 9, R9), and the repeat is exactly what a read-only surface causes.
//
// WHAT IT IS NOW. D1 -- Cloudflare's SQLite, bound as the DB binding -- holding the three
// things that must survive the cluster being gone, keyed by name so a reader never has to guess
// a schema:
//
//   founder_instructions   what the founder said, in order, with the surface it was said on.
//                          The estate's instruction ledger, edged (catalog/census/instruction.py
//                          is the laptop half; this is the half that answers while the laptop
//                          is asleep).
//   active_claims          who is working on what. AGENTS.md section 5 says the claim of record
//                          is the GitHub issue; this is the read model the founder's surface can
//                          show live without a GitHub token in a browser.
//   fencing_tokens         the fencing token of the last write, per key. A writer that lost the
//                          network and came back must not overwrite a newer decision with an
//                          older one, so every write carries (or receives) a monotonic counter
//                          and a write whose token is not greater than the stored one is refused
//                          -- the standard fencing rule, and the reason this store is safe to
//                          write from two places at once.
//
// WHAT IT IS STILL NOT. No budget, no ledger, no trace, no router state. D1 is a store and this
// module is one table read and one table write per request. Every absence stays load-bearing: a
// spent key or a lost Postgres still cannot stop it answering, because it never asks either.
//
// AUTHORITY IS SAID OUT LOUD. The state answers `"authority": "cloud-edge-d1"` -- not
// `cloud-read-only`, and never `github-canonical`, because GitHub is not where this lives. A
// reader that used to skip the surface on seeing "read-only" can now trust the word it reads.

const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS brain_state (
     key         TEXT PRIMARY KEY,
     value       TEXT NOT NULL,
     fencing     INTEGER NOT NULL DEFAULT 0,
     updated_at  TEXT NOT NULL,
     written_by  TEXT NOT NULL DEFAULT ''
   )`,
  `CREATE TABLE IF NOT EXISTS brain_instructions (
     id          INTEGER PRIMARY KEY AUTOINCREMENT,
     at          TEXT NOT NULL,
     surface     TEXT NOT NULL DEFAULT '',
     text        TEXT NOT NULL,
     session_id  TEXT NOT NULL DEFAULT '',
     fencing     INTEGER NOT NULL DEFAULT 0
   )`,
];

/** The three keys the founder's surface names, and the shape each one reports as. */
const KEYS = ["founder_instructions", "active_claims", "fencing_tokens"];

function json(body, status = 200, extra = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store", ...extra },
  });
}

function nowIso() {
  return new Date().toISOString();
}

/** Create the two tables. Idempotent, and cheap enough to run before a read that found nothing. */
async function ensure(db) {
  for (const ddl of SCHEMA) await db.prepare(ddl).run();
}

function parseValue(raw, fallback) {
  if (raw === null || raw === undefined) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

/**
 * GET: the whole brain state, in one read.
 *
 * A missing table is not an error -- it is a Worker that has never been written to, and the
 * answer for that is the honest empty state and status 200, so a founder surface renders an
 * empty board instead of a 500 page. `seeded` says which of the three came back empty, because
 * "the estate has no claims" and "the store has no claims key" are different facts and a reader
 * must be able to see which one it is looking at.
 */
async function readState(db) {
  await ensure(db);
  const keys = {};
  const seeded = [];
  for (const key of KEYS) {
    const row = await db
      .prepare("SELECT value, fencing, updated_at, written_by FROM brain_state WHERE key = ?")
      .bind(key)
      .first();
    if (!row) {
      keys[key] = key === "fencing_tokens" ? {} : [];
      seeded.push(key);
      continue;
    }
    keys[key] = parseValue(row.value, key === "fencing_tokens" ? {} : []);
  }
  const instr = await db
    .prepare("SELECT id, at, surface, text, session_id FROM brain_instructions ORDER BY id DESC LIMIT 100")
    .all();
  const rows = (instr?.results ?? []).reverse();
  // `founder_instructions` is served from its own table, which is why appends are ordered and
  // cheap; the brain_state row of the same name is kept in step so a reader that wants one key
  // and a reader that wants the list see the same history.
  if (rows.length) keys.founder_instructions = rows;
  return { keys, seeded, count: rows.length };
}

/**
 * POST: one append or one write, fenced.
 *
 * Body shapes, all of them small:
 *   {"instruction": "text", "surface": "voice", "session_id": "..."}   -- append an instruction
 *   {"key": "active_claims", "value": <any JSON>, "fencing": 7}         -- replace one key
 *   {"key": "fencing_tokens", "value": {...}, "fencing": 7}
 *
 * A write whose `fencing` is not greater than the stored token is refused with 409 and the
 * stored token, so a writer can catch up rather than silently clobber a newer decision. A write
 * with no `fencing` receives the next token from the store itself, which is the ordering a
 * single unlucky writer wants and the reason a laptop that went to sleep for an hour is safe.
 */
async function writeState(db, body, url) {
  await ensure(db);
  const who = String(body?.written_by || body?.surface || "edge").slice(0, 64);

  if (typeof body?.instruction === "string" && body.instruction.trim()) {
    const text = body.instruction.trim();
    const at = nowIso();
    const next = await bumpFencing(db, "founder_instructions", body?.fencing, who, at);
    if (next.refused) return json({ error: next.refused, fencing: next.stored }, 409);
    const ins = await db
      .prepare("INSERT INTO brain_instructions (at, surface, text, session_id, fencing) VALUES (?,?,?,?,?)")
      .bind(at, String(body?.surface || url.searchParams.get("surface") || "edge").slice(0, 64),
            text.slice(0, 8000), String(body?.session_id || "").slice(0, 128), next.fencing)
      .run();
    // Keep the mirror row current so a reader taking only `founder_instructions` from
    // brain_state still sees this instruction.
    const all = await db
      .prepare("SELECT id, at, surface, text, session_id FROM brain_instructions ORDER BY id DESC LIMIT 100")
      .all();
    const value = JSON.stringify((all?.results ?? []).reverse());
    await db
      .prepare(
        "INSERT INTO brain_state (key, value, fencing, updated_at, written_by) VALUES (?,?,?,?,?) " +
          "ON CONFLICT(key) DO UPDATE SET value=excluded.value, fencing=excluded.fencing, " +
          "updated_at=excluded.updated_at, written_by=excluded.written_by",
      )
      .bind("founder_instructions", value, next.fencing, at, who)
      .run();
    return json({
      ok: true,
      status: "written",
      authority: "cloud-edge-d1",
      appended: { id: ins?.meta?.last_row_id ?? null, at, surface: body?.surface || "edge" },
      fencing: next.fencing,
    });
  }

  const key = typeof body?.key === "string" ? body.key.trim() : "";
  if (!KEYS.includes(key) || key === "founder_instructions") {
    return json(
      {
        error: `key must be one of active_claims, fencing_tokens (founder_instructions is written with {"instruction": ...})`,
      },
      400,
    );
  }
  const at = nowIso();
  const next = await bumpFencing(db, key, body?.fencing, who, at);
  if (next.refused) return json({ error: next.refused, fencing: next.stored }, 409);
  const value = JSON.stringify(body?.value ?? (key === "fencing_tokens" ? {} : []));
  await db
    .prepare(
      "INSERT INTO brain_state (key, value, fencing, updated_at, written_by) VALUES (?,?,?,?,?) " +
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, fencing=excluded.fencing, " +
        "updated_at=excluded.updated_at, written_by=excluded.written_by",
    )
    .bind(key, value, next.fencing, at, who)
    .run();
  if (key === "active_claims") await mirrorFencing(db, next.fencing, at, who);
  return json({ ok: true, status: "written", authority: "cloud-edge-d1", key, fencing: next.fencing });
}

/** The fencing rule, in one place: a token that does not exceed the stored one is refused. */
async function bumpFencing(db, key, proposed, who, at) {
  const row = await db
    .prepare("SELECT fencing FROM brain_state WHERE key = ?")
    .bind(key)
    .first();
  const stored = Number(row?.fencing ?? 0);
  const asked = Number(proposed);
  if (Number.isFinite(asked) && proposed !== undefined && proposed !== null && asked <= stored) {
    return { refused: `fencing ${asked} does not exceed the stored ${stored}`, stored };
  }
  return { fencing: Number.isFinite(asked) && asked > stored ? asked : stored + 1, stored };
}

/** Keep the `fencing_tokens` key truthful without a second round trip from the writer. */
async function mirrorFencing(db, fencing, at, who) {
  const row = await db
    .prepare("SELECT value FROM brain_state WHERE key = 'fencing_tokens'")
    .bind()
    .first();
  const tokens = parseValue(row?.value, {});
  const merged = typeof tokens === "object" && tokens ? { ...tokens, active_claims: fencing } : { active_claims: fencing };
  await db
    .prepare(
      "INSERT INTO brain_state (key, value, fencing, updated_at, written_by) VALUES ('fencing_tokens',?,?,?,?) " +
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, fencing=excluded.fencing, " +
        "updated_at=excluded.updated_at, written_by=excluded.written_by",
    )
    .bind(JSON.stringify(merged), fencing, at, who)
    .run();
}

export async function handleBrain(request, env, url) {
  const db = env?.DB;
  if (!db) {
    // An unbound D1 is a deploy that has not run the bind step, and saying so in the answer is
    // the difference between a five-minute fix and an afternoon of guessing.
    return json(
      {
        error: "no DB binding: this Worker has no D1 database bound as DB",
        authority: "cloud-edge-d1",
        remedy: "bin/idp-edge-cutover --bind-d1",
      },
      503,
    );
  }
  if (request.method === "GET" || request.method === "HEAD") {
    const { keys, seeded, count } = await readState(db);
    return json({
      status: "live",
      authority: "cloud-edge-d1",
      home: "cloudflare-edge",
      at: nowIso(),
      // The words the old surface used, kept as an explicit contradiction so a stale client
      // cannot read this answer and conclude nothing changed: this is NOT read-only.
      readOnly: false,
      instructions: count,
      ...keys,
      seeded,
    });
  }
  if (request.method === "POST" || request.method === "PUT") {
    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "body is not JSON" }, 400);
    }
    return writeState(db, body, url);
  }
  return json({ error: "method not allowed" }, 405);
}

export { KEYS, SCHEMA };

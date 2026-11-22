import { LANE, REPO, b64ToBytes, sha256Hex } from "../src/aistudio.js";
import { gitBlobSha } from "../src/aistudio-fence.js";

export function bytesToB64(bytes) {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

export async function encodeFiles(files) {
  return Promise.all(
    files.map(async (file) => {
      const bytes = new TextEncoder().encode(file.content);
      return {
        path: file.path,
        content_b64: bytesToB64(bytes),
        sha256: await sha256Hex(bytes),
        bytes: bytes.length,
      };
    }),
  );
}

export const SOURCE_FILES = [
  { path: "src/engine/routerCore.ts", content: "const lanes = 4;\n" },
  { path: "src/data/generalPurposePersonaData.ts", content: "export const personas = [];\n" },
];

export function makeFetch(existing = [], options = {}) {
  const journal = [];
  const head = existing.length > 0 ? "b".repeat(40) : null;
  const mainHead = "a".repeat(40);

  const fetchImpl = async (url, init = {}) => {
    const parsed = new URL(url);
    const method = (init.method || "GET").toUpperCase();
    let body = null;
    if (typeof init.body === "string") {
      try {
        body = JSON.parse(init.body);
      } catch {
        body = init.body;
      }
    }
    journal.push({ method, path: parsed.pathname, body });

    const ok = (value, status = 200) =>
      new Response(JSON.stringify(value), {
        status,
        headers: { "content-type": "application/json" },
      });

    if (parsed.pathname === "/v1/github/installation-token") {
      return ok(options.brokerResponse ?? {
        schema: "MERIDIAN-GITHUB-LEASE-v1",
        repository: REPO,
        lane: "application-engineer",
        permissions: { metadata: "read", contents: "write", issues: "write" },
        token: "ghs_" + "x".repeat(48),
        expires_at: new Date(Date.now() + 3_300_000).toISOString(),
      });
    }
    if (parsed.pathname === `/repos/${REPO}/git/ref/heads/${LANE}`) {
      return head
        ? ok({ ref: `refs/heads/${LANE}`, object: { sha: head, type: "commit" } })
        : new Response("{}", { status: 404 });
    }
    if (parsed.pathname === `/repos/${REPO}/git/ref/heads/main`) {
      return ok({ ref: "refs/heads/main", object: { sha: mainHead, type: "commit" } });
    }
    if (parsed.pathname === `/repos/${REPO}/git/commits/${head || mainHead}`) {
      return ok({ sha: head || mainHead, tree: { sha: "tree0" } });
    }
    if (parsed.pathname === `/repos/${REPO}/git/trees/tree0`) {
      return ok({
        tree: existing.map((file) => ({ path: file.path, sha: file.sha, type: file.type || "blob", mode: file.mode || "100644" })),
        truncated: false,
      });
    }
    if (parsed.pathname === `/repos/${REPO}/git/blobs`) {
      return ok({ sha: await gitBlobSha(b64ToBytes(body.content)) });
    }
    if (parsed.pathname === `/repos/${REPO}/git/trees`) return ok({ sha: "tree1" });
    if (parsed.pathname === `/repos/${REPO}/git/commits`) return ok({ sha: "c".repeat(40) });
    if (parsed.pathname === `/repos/${REPO}/git/refs/heads/${LANE}`) return ok({});
    if (parsed.pathname === `/repos/${REPO}/git/refs`) return ok({});
    if (parsed.pathname === `/repos/${REPO}/issues/8133/comments`) return ok({ id: 1 });
    if (parsed.pathname === `/repos/${REPO}/actions/workflows/greenlane.yml/dispatches`) {
      return new Response(null, { status: 204 });
    }
    if (parsed.pathname === "/realtime") return ok({});
    return ok({});
  };

  return { fetchImpl, journal };
}

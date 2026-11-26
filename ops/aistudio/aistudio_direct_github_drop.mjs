// AI Studio direct source custody, not production authority.
// Supply a short-lived, repo-scoped host credential in memory only.
const REPO = "chidionyema/idp";
const ROOTS = new Set(["src", "tests", "packages", "platform", "docs", "bin", "scripts", "ops", "catalog"]);
const DENIED = new Set([".git", ".github", ".githooks", ".ssh", ".env", "node_modules", "secrets", "secret", "credentials", "credential", "private", ".vault"]);
const PROTECTED = new Set(["bin/idp-auth", "bin/idp-guarded-paths", "bin/idp-ci-guarded-paths", "catalog/dof-registry.json", "catalog/genesis-protocols.json", "platform/edge/otel-endpoint-exception.yaml", "platform/edge/inject-otel-endpoint.yaml", "platform/edge/require-otel-endpoint.yaml"]);
const SECRET = /-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|github_pat_[A-Za-z0-9_]{12,}|\bgh[pousr]_[A-Za-z0-9]{16,}|\bsk-[A-Za-z0-9_-]{16,}|\bAIza[A-Za-z0-9_-]{30,}|\bAKIA[A-Z0-9]{16}/i;
const encoder = new TextEncoder();

export async function sha256(value) {
  const hash = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return Array.from(new Uint8Array(hash), x => x.toString(16).padStart(2, "0")).join("");
}

export async function sanitizeAndValidate(files, release) {
  if (release?.repo !== REPO || release.public_release !== true ||
      !/^[0-9a-f]{40}$/.test(release.base_sha) ||
      !Array.isArray(release.files) || !Array.isArray(files) ||
      files.length === 0 || files.length > 5 || files.length !== release.files.length) {
    throw new Error("RELEASE_SCOPE");
  }
  const approved = new Map(release.files.map(f => [f.path, f.sha256]));
  if (approved.size !== files.length) throw new Error("RELEASE_DUPLICATE");
  const seen = new Set();
  for (const file of files) {
    const {path, content} = file;
    if (typeof path !== "string" || !/^[A-Za-z0-9._/-]{1,200}$/.test(path)) throw new Error("PATH");
    const parts = path.split("/");
    if (parts.length < 2 || !ROOTS.has(parts[0]) || parts.some(p =>
        !p || p === "." || p === ".." || DENIED.has(p.toLowerCase()) || p.toLowerCase().startsWith(".env")) ||
        PROTECTED.has(path) || path.startsWith("platform/policies/kyverno/") ||
        /\.(pem|key|p12|pfx|age|kdbx|sqlite|db|env)(\.|$)/i.test(path) ||
        /generalPurposePersonaData\.ts|physicalEstateData\.ts|INITIAL_SPECIALIST_FLEET/.test(path) ||
        seen.has(path)) throw new Error("PATH_SCOPE");
    seen.add(path);
    if (typeof content !== "string" || encoder.encode(content).length > 262144 ||
        content.includes("\0") || SECRET.test(content) ||
        await sha256(content) !== approved.get(path)) throw new Error("CONTENT_SCOPE");
  }
  return files.map(({path, content}) => ({path, content}));
}

export async function pushDirectToGitHub({token, files, release, fetchImpl = fetch}) {
  if (!token) throw new Error("MISSING_HOST_CREDENTIAL");
  const accepted = await sanitizeAndValidate(files, release);
  const api = "https://api.github.com/repos/" + REPO;
  async function gh(path, method = "GET", body) {
    const response = await fetchImpl(api + path, {
      method, redirect: "error", signal: AbortSignal.timeout(20000),
      headers: {Authorization: "Bearer " + token, Accept: "application/vnd.github+json", "Content-Type": "application/json"},
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) throw new Error("GITHUB_HTTP_" + response.status);
    return response.json();
  }
  const main = await gh("/git/ref/heads/main");
  if (main.object.sha !== release.base_sha) throw new Error("STALE_BASE");
  const base = await gh("/git/commits/" + main.object.sha);
  const tree = [];
  for (const file of accepted) {
    const blob = await gh("/git/blobs", "POST", {content: file.content, encoding: "utf-8"});
    tree.push({path: file.path, mode: "100644", type: "blob", sha: blob.sha});
  }
  const next = await gh("/git/trees", "POST", {base_tree: base.tree.sha, tree});
  const digest = await sha256(JSON.stringify(accepted.slice().sort((a,b) => a.path.localeCompare(b.path))));
  const commit = await gh("/git/commits", "POST", {
    message: "chore: AI Studio public source custody\n\nDrop-SHA256: " + digest,
    tree: next.sha, parents: [release.base_sha],
  });
  const branch = "quarantine/aistudio-" + digest;
  // Never overwrite a previously published ref, even on a 422 collision.
  await gh("/git/refs", "POST", {ref: "refs/heads/" + branch, sha: commit.sha});
  return {branch, commit_sha: commit.sha, status: "SOURCE_CUSTODY_ONLY", operational_yield: 0};
}

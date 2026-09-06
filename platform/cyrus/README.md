# Cyrus

Cyrus is the agent that picks up an issue from Linear or GitHub, opens a worktree, runs an
engine in it and opens a pull request. It holds no cluster verbs: Flux reconciles what it
proposes.

## What the manifest claimed and the pod did

Everything below was measured in the running pod on 2026-09-06, against the installed
`cyrus-ai` 0.2.71 distribution, not read off the manifest. Four walls stood between a green
build and an agent that could do anything, and each one left the pod reporting success.

### 1. The config file was mounted where nothing reads it

`CYRUS_CONFIG_PATH` was set in the deployment and is read by no code in the package. Cyrus
resolves its configuration from `--cyrus-home`, default `resolve(homedir(), ".cyrus")`
(`dist/src/app.js:41`), and the ConfigMap was mounted at `/config`. The pod's own log named
the file it was waiting for:

```
[INFO] [EdgeWorker] Watching config file for changes: /home/node/.cyrus/config.json
...
No repositories configured
   Add one with: cyrus self-add-repo <git-url>
```

Three repositories sat in the ConfigMap the whole time. Fixed by mounting `config.json` at
that path with a `subPath`, so the rest of the home tree stays writable.

### 2. The server bound loopback, and the probes asked for a route that does not exist

`const serverHost = config.serverHost || "localhost"` (`cyrus-edge-worker/EdgeWorker.js:255`).
The kubelet probes the pod IP, so every probe was refused while the log said
`Edge worker started successfully`:

```
Liveness probe failed: Get "http://10.244.1.195:3456/health":
  dial tcp 10.244.1.195:3456: connect: connection refused
```

Both probes also asked for `/health`, and cyrus serves no such route: `EdgeWorker` registers
`GET /status` and `GET /version`, and the shared server registers `/callback`,
`/linear-webhook`, `/github-webhook`, `/gitlab-webhook`, `/slack-webhook`, `/robots.txt`,
`/approval`, `/proxy` and `/oauth/authorize`. `serverHost: "0.0.0.0"` is now in the
ConfigMap and both probes ask for `/status`.

### 3. Every credential variable was dead

Counting the files in the installed distribution that reference each name:

| set in the deployment | files | what cyrus reads | files |
|---|---|---|---|
| `GH_TOKEN_FILE` | 0 | `GITHUB_TOKEN` | 2 |
| `LINEAR_WEBHOOK_SECRET_FILE` | 0 | `LINEAR_WEBHOOK_SECRET` | 3 |
| `LINEAR_API_TOKEN_FILE` | 0 | `LINEAR_API_TOKEN` | 1 |
| `GITHUB_WEBHOOK_SECRET_FILE` | 0 | `GITHUB_WEBHOOK_SECRET` | 4 |

So cyrus ran with no credentials at all, and registered every transport in *proxy mode* —
the mode that expects a bearer token from cyrus's own hosted service and verifies no
sender signature (`EdgeWorker.js:566`):

```
[INFO] [LinearEventTransport] Registered POST /linear-webhook endpoint (proxy mode)
[INFO] [GitHubEventTransport] Registered POST /github-webhook endpoint (proxy mode)
```

`GH_TOKEN_FILE` also named `/secrets/github/token`, while the ExternalSecret writes the key
`CYRUS_GITHUB_TOKEN`, so the path was wrong as well as unread — `cannot open
/secrets/github/token: No such file` in the live pod.

`entrypoint.sh` reads the mounted files and exports the names cyrus reads, and
`CYRUS_HOST_EXTERNAL=true` takes the transports out of proxy mode so cyrus verifies the
signatures itself. The credentials stay files mounted from the vault and never enter this
manifest, which is what the edge policy protects. Cyrus offers one other road for a token,
`config.linearWorkspaces[<id>].linearToken` in `config.json`, and for Linear it is the only
road (wall 7): the entrypoint joins the mounted token into the pod's private copy of the
file, and the ConfigMap in git never carries it.

### 4. Cyrus never clones

`GitService` runs `git worktree add` with `cwd` set to `repositoryPath` and reports
`<path> is not a git repository` when that path is absent (`GitService.js:476`). There is
no clone path anywhere in the package. `/repo` is an `emptyDir` and starts empty on every
restart, so all three configured repositories pointed at nothing.

The `clone-repos` init container makes them exist, reading the same `config.json` cyrus
will read. They are blobless partial clones (`--filter=blob:none`): full history, so
`git worktree add` can reach any branch, without downloading every file of every past
revision. It runs as an init container rather than inside the entrypoint because a clone
that outlasts `initialDelaySeconds` would be killed by the liveness probe halfway through.

`/repo` is an `emptyDir` and not a PersistentVolumeClaim on purpose: the OCI block volume
class is ReadWriteOnce, and a RWO volume plus a rolling update is the deadlock this
namespace has already hit once through its CPU quota. Re-cloning three blobless repositories
on a restart is cheaper than that failure mode.

## Why the token never reaches a command line

git authenticates through a `GIT_ASKPASS` helper that cats the mounted secret. A token in
`argv` is readable by anything that can run `ps` (LAW 10). The helper reads the file on
every invocation rather than capturing it once, because the value is a GitHub App
installation token: valid for an hour, rewritten by External Secrets every ten minutes. A
long-lived pod that cached it would begin failing after an hour with no change to blame.

### 5. The obvious way to mount one file made the home directory unwritable

Mounting `config.json` with a `subPath` straight at `~/.cyrus/config.json` is the shape the
Kubernetes documentation reaches for, and it crash-looped the pod:

```
[ERROR] [CLI] Failed to create directory /var/lib/cyrus/.cyrus/mcp-configs:
  Error: EACCES: permission denied, mkdir '/var/lib/cyrus/.cyrus/mcp-configs'
```

Kubelet creates the intermediate directory for a `subPath` mount itself, root-owned and not
group-writable, and `fsGroup` does not reach it. Cyrus creates `repos`, `worktrees` and
`mcp-configs` beside its config file on its first action, so it died there every time.

The ConfigMap now mounts read-only at `/etc/cyrus` and the entrypoint makes `~/.cyrus` as
the running uid and links the config in. A ConfigMap change still reaches cyrus through
the link.

### 6. A symlink into the ConfigMap, and cyrus writes its own config back

The fix for wall 5 mounted the ConfigMap read-only at `/etc/cyrus` and had the entrypoint
symlink it into `~/.cyrus/config.json`. The pod then got past the directory creation, read the
three repositories, and died on its first action:

```
[INFO ] [CLI] [Migration] Added "Skill" to allowedTools for repository: idp
[INFO ] [CLI] [Migration] Added "Skill" to allowedTools for repository: crew
[INFO ] [CLI] [Migration] Added "Skill" to allowedTools for repository: hermes-v2
[ERROR] [CLI] Failed to start edge application: EROFS: read-only file system,
              open '/var/lib/cyrus/.cyrus/config.json'
```

Cyrus migrates its own config on boot and writes the migrated document straight back, so its
config file cannot live on a read-only mount under any name. The entrypoint copies rather than
links, and re-copies on every start: git is the source of truth, and whatever cyrus wrote during
the last boot is discarded instead of accumulating in an emptyDir that outlives nothing anyway.

The clone step, on the same image, worked first time:

```
cyrus-entrypoint: cloning https://github.com/chidionyema/idp into /repo/idp
cyrus-entrypoint: cloning https://github.com/chidionyema/crew into /repo/crew
cyrus-entrypoint: cloning https://github.com/chidionyema/hermes-v2 into /repo/hermes-v2
cyrus-entrypoint: checkouts ready
```

The three `is not readable` lines above it are the init container, which mounts the GitHub
secret and not the webhook secret, and they are the message the entrypoint exists to print: a
credential that is absent says so, rather than becoming an empty string that reaches a
signature check.

### 7. Linked to no Linear workspace, and the key the vault holds is not a token cyrus can send

Past the EROFS exit, on image `main-5300`, the pod read its three repositories and died on the
next line:

```
[INFO ] [GitLabEventTransport] Registered POST /gitlab-webhook endpoint (proxy mode)
[ERROR] [CLI] Failed to start edge application: Repository "idp" is not linked to a Linear workspace
```

`cyrus-core` `requireLinearWorkspaceId()` throws that for any active repository without a
`linearWorkspaceId`, and `PromptBuilder.generateRoutingContextForAllWorkspaces()` walks every
active repository at start. The id is the Linear organisation id, which the vault's key
answers (`{ organization { id urlKey } }` → `ec650f84-2971-4e51-8991-bda953c00d5e`,
`crewestate`); it is not a secret and sits on each repository in `configmap.yaml`.

The token cannot follow it into git, and there is no environment variable cyrus reads for it:
`grep -rn 'process.env.LINEAR' cyrus-edge-worker/dist` finds only `LINEAR_DIRECT_WEBHOOKS`,
`LINEAR_WEBHOOK_SECRET`, `LINEAR_CLIENT_ID` and `LINEAR_CLIENT_SECRET`. The single road is
`config.linearWorkspaces[<id>].linearToken`, so `entrypoint.sh` joins the mounted file into
the pod's copy of `config.json` with `jq`, after the copy of wall 6 and before `exec cyrus`.

That gets the pod up and the GitHub door open. It does not make the Linear door work, and the
reason was measured before this file claimed otherwise. Cyrus builds its client as
`new LinearClient({ accessToken })` (`EdgeWorker.js:302`), and `@linear/sdk` sends that as
`Authorization: Bearer <token>` unconditionally (`index.cjs:117060`). Linear refuses a
personal API key in that shape:

```
$ curl -H "Authorization: Bearer $LINEAR_API_KEY" https://api.linear.app/graphql ...
{"errors":[{"message":"It looks like you're trying to use an API key as a Bearer token.
  Remove the Bearer prefix from the Authorization header." ...
```

The same key without the prefix answers the organisation query above, so the key is good and
the transport is the mismatch. `cyrus-linear-api-token` in the human vault therefore has to
become an OAuth access token (plus its refresh token as `linearRefreshToken`, with
`LINEAR_CLIENT_ID`/`LINEAR_CLIENT_SECRET` for cyrus's own refresh) before a Linear issue can
reach this pod. An OAuth token is born the same way the key was, in a browser, once: a Linear
OAuth application in the workspace and one consent. Until that exists the Linear transport
is `MEASURED_FAIL` at the first API call, and the GitHub transport is the door in use.

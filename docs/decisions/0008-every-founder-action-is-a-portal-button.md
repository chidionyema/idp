# 0008. Every founder action is a portal button; the terminal is for machines

- Status: PROPOSED 2026-08-28 (crew#66). Founder wording, verbatim, 2026-08-28: "needs everything
  from backstage" / "design full founder self service features for estate using backstage" / "to
  allow founder to fully self service infra, stack, apps, need thorough audit, research, online
  platform engineering elite level".
- Date: 2026-08-28
- Deciders: founder
- Affects: `backstage/` (templates, app-config, permission policy), `platform/backstage/` (the
  pod's credential), `platform/github-app/lanes.json`, every `.github/workflows/*.yml` that
  carries `workflow_dispatch`, and every `bin/*` that today prints a command for a person.

## The measurement, 2026-08-28 21:5xZ

Two audits, one of this repo and one of the field, both on the record (crew#66).

**This repo.** The portal can already press buttons: `@backstage/plugin-scaffolder-backend-module-github`
is installed, so `github:actions:dispatch` is a step a template may run. Nothing uses it. One
template exists (`backstage/templates/estate-component`) and it only renders files. Thirteen
workflows carry `workflow_dispatch` and none has a button: catalog-render, drill-heartbeat,
kini-finish, kyverno-secrets-drill, login-drill, oke-check, ping, portability-drill, stale,
trace-drill, vault-seed, verify-drill, wake-blocked. The running pod holds no GitHub credential:
`backstage/app-config.yaml:66-71` reads `${GITHUB_TOKEN}`, and the mounted secret `backstage-env`
(`platform/backstage/overlays/oke/backstage-external-secret.yaml`) carries only `BACKEND_SECRET`
and `POSTGRES_PASSWORD`. So a button, had one existed, could not fire. The permission backend is
installed with the allow-all policy (`backstage/app-config.yaml:185`), the Kubernetes plugin is
installed with no cluster in the dev profile (`app-config.yaml:181`), the notifications plugin and
its scaffolder module are installed and unused.

Twelve places a person's hands are required, with the file that asks for them:

| what the hand does | where | portal-shaped? |
|---|---|---|
| taps Create on the GitHub App manifest URL | `bin/idp-github-app:8` | link |
| signs in to the OCI console as tenancy owner | `bin/idp-oci-bootstrap:44` | link only (external console) |
| `gh secret set` × 5 for oke-check | `docs/how-to/check-the-cluster-from-github.md:15` | no: GitHub settings UI |
| fixes Actions billing at a settings URL | `bin/idp-actions-refused:20` | link |
| types `APPROVE: <word>` on a PR | `bin/pr-report:34`, `.github/workflows/founder-word.yml` | button |
| types `FINISH: KINI` on an issue | `.github/workflows/kini-finish.yml` | button |
| `gh workflow run vault-seed.yml -f entry=…` | `.github/workflows/vault-seed.yml:4` | button |
| `gh workflow run oke-check.yml -f mode=… -f playbook=…` | `.github/workflows/oke-check.yml:4` | button |
| silences an alert in Alertmanager during a drain | `bin/idp-oke-break-glass:368` | button (custom action) |
| pipes a credential file into `scripts/secret-add` | `docs/how-to/store-a-credential.md:9` | no: a value must never cross a browser |
| `kubectl port-forward` to the unrouted portal | `backstage/app-config.container.yaml` | no: the fix is a route, not a button |
| deletes the OIDC app in the OCI console on drift | `bin/idp-oci-bootstrap:173` | link only |

**The field.** The scaffolder's `github:actions:dispatch` fires a workflow and returns no run id
(backstage/backstage#29727, #33104), so a button that says "done" needs a follow-up step that finds
the run. The GitHub identity an elite portal uses is a GitHub App with `actions:write`, `contents`
and `pull_requests` on the named repos, its key reaching the pod as an ExternalSecret, never a PAT
in config. The permission framework gates a template, a step or a single parameter by
`backstage:permissions` tag, and every run lands as a `scaffolder.task.execute` audit event. The
Flux plugin carries real sync/suspend/resume buttons behind a permission; the Kubernetes plugin is
read-only and mutation is a named custom action. Terraform never runs inside Backstage: a template
dispatches the workflow that plans, posts the plan to the entity page, and applies behind a second
gate. `notification:send` plus Signals closes the loop without a refresh. Port, Cortex, Humanitec,
Roadie and Spotify Portal converge on one shape: a catalogue of actions bound to an entity, an
approval gate per action, the result on the entity page, and a scorecard; the CNCF platform
maturity model grades it Provisional → Operational → Scalable → Optimizing. Sources are in the
research note attached to crew#66.

## The decision

1. **A founder action is a Backstage template or nothing.** A `bin/*` that ends by printing a
   command for a person, or a doc step that says "run", is a defect of the same class as a
   password over Telegram (ADR 0007): the thing that has to travel is the founder's attention.
   The one exception is a credential value, which never crosses a browser (R49); that stays
   `scripts/secret-add`, and the button that follows it seeds from the store.
2. **The buttons are generated, not written.** `bin/idp-portal-buttons` (crew#66 branch
   `feat/crew66-self-service-portal`) turns every `workflow_dispatch` block into a template under
   `backstage/templates/founder-actions/<workflow>/`, a choice becoming a drop-down and a default
   staying a default, with `github:actions:dispatch` as its only step. `--check` fails CI when a
   dispatchable workflow has no button or a stale one. Nobody hand-writes a template for a workflow.
3. **The portal's GitHub identity is the estate App on its own lane.** `platform/github-app/lanes.json`
   gains lane `founder-actions` (`actions:write`, `contents:read`, `issues:write`,
   `pull_requests:write` on `idp`, `crew`, `claude-guards`); its installation token reaches the pod
   as `GITHUB_TOKEN` in the `backstage-env` ExternalSecret from the vault, nowhere else.
4. **One owner, one policy.** The allow-all policy is replaced by one that lets a
   `founder-actions/*` template run only for the founder's identity and the platform group, logs
   every `scaffolder.task.execute` to the estate collector (LAW 50), and refuses the rest with the
   reason on screen.
5. **Every mutating button ends with `notification:send`** and a link to the run it started
   (the follow-up `http:backstage:request` step that lists the workflow's runs after dispatch).
6. **Day-2 is a plugin, not a script.** The Kubernetes plugin gets the `estate` cluster read-only;
   the Flux plugin gets sync/suspend behind the same policy; the four repair paths today typed
   into `oke-check` are its drop-down. Alertmanager silence and `APPROVE:`/`FINISH:` words become
   buttons of the same generated shape (a workflow that posts the comment on the founder's behalf).
7. **The catalog entity is the console.** `backstage/catalog-info.yaml` stops being the
   create-app example (`owner: john@example.com`); every product and platform layer carries its
   buttons, its runs, its drills row and its scorecard on its own page.

## Checkpoints (crew#66)

| CP | done means | proved by |
|---|---|---|
| 1 | lane `founder-actions` in lanes.json; `GITHUB_TOKEN` in the pod from the vault | `kubectl -n backstage get externalsecret backstage-env -o jsonpath='{.spec.data[*].secretKey}'` lists GITHUB_TOKEN; app-config carries no literal |
| 2 | 13 generated templates on main; `bin/idp-portal-buttons --check` in `bin/idp-ci` | catalog lists 13 `founder-actions/*`; a 14th `workflow_dispatch` with no button turns CI red |
| 3 | founder presses **ping** in the portal; the run appears under Actions | `scaffolder.task.execute` row in the collector + run URL in the task output, same minute |
| 4 | permission policy: founder + platform only; audit to collector | a second identity is refused with the reason; the refusal row is queryable |
| 5 | `notification:send` on every mutating template | notification visible in the portal within the run's duration |
| 6 | Kubernetes read-only + Flux sync/suspend on `estate` | `kubectl auth can-i create pods --as=<portal sa>` = no; a Flux suspend from the portal is a reconciliation event |
| 7 | `APPROVE:`, `FINISH: KINI`, Alertmanager silence, vault-seed, oke-check repair as buttons | each pressed once by the founder; `Founder receipt:` on crew#66 |
| 8 | zero `bin/*` printing a command for a person | `grep -lE 'run: |FOUNDER ACTION' bin/*` returns only the credential-value path |

## Consequences

- A workflow's `workflow_dispatch.inputs` block is now the UI spec; a bad `description` is a bad
  button, and the review reads it as such.
- The portal becomes a mutating surface, so its route (today `kubectl port-forward`) and its
  login (ADR 0007) come before CP3, not after.
- The founder no longer needs `gh`, `kubectl` or a terminal for any listed step; the estate keeps
  them for machines.

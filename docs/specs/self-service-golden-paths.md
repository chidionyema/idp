# Self-service golden paths: spec (crew#627 CP2)

## What the founder asked for

Standing up a new service today means someone hand-writes everything: the
repository, the messaging setup, the payment hookup, the CI checks, the
security scans, and the platform config that gets it running in the cluster.
The founder wants one place where a person picks a stack — Python, .NET, or
Node — and gets a service that already has the estate's standards, test
libraries, GitHub setup, code scanners, and infra wired in, without anyone
hand-writing any of it. That includes the estate guards (the shell and
Python checks in `~/.estate`, installed automatically the way
`hermes-v2#52` does it) so a new repo cannot drift from the standard from
day one.

## What already exists (no re-building)

Backstage Scaffolder is installed (`idp/backstage`). A template called
`estate-component` already creates a repo, registers it in the catalogue,
and stops there — no infra, no standards, no guards. `enable-platform-feature`
is a second template. Neither stack (Python, .NET, Node) has its own golden
path yet. Infra for a running service today is a hand-written folder under
`platform/<name>/` (see `platform/prospector`) that Flux reconciles from
`idp/clusters/oke`. Secrets come from External Secrets Operator over OCI
Vault, never typed in. Standards already named on the board: Next.js +
Payload for front ends, Apprise for notifications, SigNoz/OpenTelemetry for
observability, GitHub Actions for CI, ruff for Python code quality.

## Per-stack golden path: what a new service gets, one row per stack

| Stack | Repo scaffold | Tests | CI | Scanners/security | Messaging | Payments | Guards |
|---|---|---|---|---|---|---|---|
| Python | Poetry project, ruff config, pre-commit | pytest + fixtures | GitHub Actions: ruff, pytest, build | ruff (already standard), pip-audit for dependencies | Apprise client wired to estate notifier | Stripe SDK stub + secret via ESO | `~/.estate` hooks via SessionStart, from git |
| .NET | dotnet new template, EditorConfig | xUnit | GitHub Actions: dotnet build/test, dotnet format | dotnet-format, a .NET SCA scanner (named at build time, not invented here) | Apprise client (HTTP) wired to estate notifier | Stripe SDK stub + secret via ESO | Same `~/.estate` hook |
| Node | npm/pnpm workspace, ESLint + Prettier config | Vitest or Jest (one, not both) | GitHub Actions: lint, test, build | ESLint security plugin, npm audit | Apprise client (HTTP) wired to estate notifier | Stripe SDK stub + secret via ESO | Same `~/.estate` hook |

Every row uses the estate's existing standard, not a new one invented per
stack. Where the standard doesn't yet name a specific tool (the .NET
scanner, the Node test runner), that is one of the two open decisions below
plus one more: it gets named once, in `crew/docs/STANDARDS.md`, not
per-template.

## The one-place flow

1. A person opens the Scaffolder in Backstage and picks "New service"
   with a stack (Python, .NET, or Node).
2. The template runs `fetch:template` with the stack's golden-path
   content from the table above baked in, `publish:github` to create
   the repo with CI, scanners and the `~/.estate` guard hook already in
   the checked-in files, and `catalog:register` for the Backstage entity.
3. The same template also opens a pull request against `idp` that adds
   `platform/<service>/` (namespace + ExternalSecrets, following the
   `platform/prospector` shape) for the service's infra.
4. Merging that PR is what makes Flux reconcile it into the cluster —
   nothing is applied by hand and nothing is applied by the template
   directly.

## Proof drill

1. Run the template for a throwaway service on each stack.
2. Confirm the repo exists, CI is green, and the catalogue entity shows
   up in Backstage.
3. Merge the opened `idp` PR and confirm Flux reconciles
   `platform/<throwaway>/` (`flux get kustomizations` shows it Ready).
4. Sign in on the throwaway service's hostname and get a real response.
5. Tear the service down: revert the `idp` PR, delete the repo, confirm
   Flux removes the namespace.

## Checkpoints (CP2a .. CP2f)

- CP2a: Golden-path content (repo files, CI, scanner config, guard hook)
  defined for Python, done when `estate-component` forked into
  `estate-service-python` produces a repo whose CI run is green.
- CP2b: Same for .NET, done when `estate-service-dotnet` produces a repo
  whose CI run is green.
- CP2c: Same for Node, done when `estate-service-node` produces a repo
  whose CI run is green.
- CP2d: Template opens the `idp` platform PR automatically, done when a
  scaffolder run for any stack produces an open PR touching only
  `platform/<service>/`.
- CP2e: Flux reconciles a template-created service end to end, done when
  `flux get kustomizations platform-<service>` reports Ready after that
  PR merges.
- CP2f: Proof drill passes on all three stacks and the throwaway service
  tears down cleanly, done when the drill in this spec runs on Python,
  .NET and Node and `flux get kustomizations` shows no trace left after
  teardown.

## Founder decisions (2026-08-30, verbatim, closing the three open questions)

1. **Mandatory in every service:** "Tracing (SigNoz/Langfuse collector), Estate Guards
   (~/.estate hooks, formatters, linters), and security/secret scanning. You cannot spin up a
   service without these." **Ticked at creation:** "Messaging, payments, and databases. These are
   modular add-ons included only when explicitly selected during the portal bootstrap."
2. **Database standard:** "Postgres Operator on the cluster for any service requiring a
   persistent, transactional database, provisioned automatically via the infra PR. Exception:
   local analytics/research scrapers (like GPT Researcher workflows) can drop down to a local
   DuckDB file, but core services default strictly to the cluster Postgres operator."
   The operator is CloudNativePG (Apache-2.0, CNCF): one `Cluster` resource per ticked service in
   `platform/<service>/`, credentials landing as a Kubernetes Secret the service reads; no other
   Postgres operator on the cluster (one of each layer, headline rule).
3. **Pull request gate:** "Lands in staging on its own (Autonomous Mode). The template generates
   the repo, configures GitHub, wires the infra PR, and Flux deploys it to staging automatically.
   No manual bottlenecks. The safety net: the system relies entirely on the automated test suite
   and CodeQL/scanners passing. If a test or a guard fails, the PR blocks itself."
   So: the infra pull request auto-merges on green; a red check is the only stop. Production is
   not touched by the template (crew ruling: staging is the only place crew infra lands).

## Scanners on from the first commit (every stack)

gitleaks (secrets), Trivy (dependencies and image), CodeQL (GitHub), plus per language:
ruff + bandit + pip-audit (Python); Roslyn analysers + `dotnet list package --vulnerable`
(.NET); eslint security plugin + `npm audit` (Node). A service the scanners do not cover cannot
be created: the template refuses to publish without the scanner workflow in the skeleton.

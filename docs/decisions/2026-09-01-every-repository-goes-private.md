# 2026-09-01. Every repository goes private, in hours, without the estate going dark

Founder, 2026-09-01, in one message: every repository is going private, plan for that; and new
crew arrive in a few hours (his exact words are on the tracked item). This is the plan. Nothing in it has been
executed; the order below starts on his word.

## What is true today (read from GitHub at 12:5xZ, not from memory)

- 30 repositories under the account are public, 3 are private (estate-secrets, haworks,
  ci-reach-heal-probe). The ones that run the estate: idp, prospector, crew, hermes-v2,
  infra-crew, hermes-agent, estate, claude-guards, claude-estate.
- The account is on GitHub Free. Proof: asking the API for the rulesets of one private repository
  answers `Upgrade to GitHub Pro or make this repository public to enable this feature`
  (HTTP 403). On Free, rulesets and protected branches work on public repositories only.
- idp carries four active rulesets today: estate-default-branch-protection, estate-security-scan,
  founder-only-releases, idp-required-checks. They are the whole of "the founder merges, and only
  green merges". The moment idp is private on Free, all four stop being enforced. Nothing in git
  changes; the fence is simply gone.
- Actions minutes are free on public repositories. On private ones the plan's allowance applies:
  Free 2,000 minutes a month, Pro 3,000 (GitHub's plans page, read today). The estate's own
  usage, measured from the billable timing of every run in the last 24 hours across idp, crew,
  prospector, hermes-v2 and infra-crew, is in the evidence section below. If that number is above
  roughly 65 a day, Free runs out inside the month and Pro does too.
- Container images on ghcr are a separate switch. Package visibility does not follow the
  repository; 9 of the estate's 11 packages are public today and stay so until changed.
- The cluster's own Git access survives: Flux reads idp over ssh with a deploy key
  (`clusters/oke/flux-system/gotk-sync.yaml`, secretRef flux-system) and pulls the catalogue image
  with the ghcr-pull secret.

## What breaks the moment the switch is flipped, and the fix for each

Found by a sweep of every checkout (idp, prospector, crew, hermes-v2, infra-crew, the guards
tree under the Claude scripts) for anything that only works while the code is public.

| # | What | Where | Fix |
|---|---|---|---|
| 1 | Every gate in every repository fails closed. Thirteen call sites check out or reuse another repository with the job's default token, which cannot read a private sibling. | `crew/.github/workflows/crew-qa.yml:84`, `crew/.github/workflows/dependencies.yml:32`, `hermes-v2/.github/workflows/gates.yml:65`, `idp/.github/workflows/fast-gate.yml:19`, `idp/.github/workflows/catalog-render.yml:50`, `idp/.github/workflows/conscience.yml:43`, `idp/.github/workflows/operating-model-gate.yml:83`; reusable `uses: chidionyema/idp/...@main` from crew, prospector and hermes-v2 (operating-model-gate, security-scan, spec-gate, wake-blocked). | Mint the estate GitHub App token in each job (`bin/idp-github-app` already does this for estate-state.yml) and pass it as `token:` on the seven checkouts. Set idp's and claude-guards' Actions access to "repositories owned by the user" by API (`PUT /repos/{repo}/actions/permissions/access`, `access_level: user`), which the reusable workflows need. |
| 2 | The portal loses the product. Backstage reads prospector's catalogue entry by public URL and proxies the live diagram from raw.githubusercontent, both carry a comment saying the repository is public so no token is needed. The GitHub integration token is `${GITHUB_TOKEN}` and that variable is not set in the catalogue pod. | `backstage/app-config.container.yaml:170-177`, `backstage/app-config.yaml:103`, `platform/backstage/base/catalogue.yaml` (no GITHUB_TOKEN) | One vault-fed secret carrying an App token into the catalogue pod as GITHUB_TOKEN; Backstage then authenticates both reads and the 47 project-slug tabs and 24 founder buttons with it. |
| 3 | The agent image cannot be rebuilt. hermes-v2's Dockerfile clones hermes-agent anonymously mid-build. | `hermes-v2/Dockerfile:31` | Clone with a build secret (`--mount=type=secret`) from the App token; the gates job already needs the same token. |
| 4 | Disaster recovery and onboarding cannot bootstrap. Three tokenless HTTPS clones and one raw curl. | `~/.claude/scripts/rebuild/bootstrap.sh:17`, `~/.claude/scripts/docs/onboarding/estate-repos.md:53`, `crew/README.md:24`, `crew/risk/REGISTER.jsonl:13` | Clone over ssh or `gh repo clone` (the machine's own login), and the risk-register evidence runs the local file, not a curl. |
| 5 | Silent blindness that pages nobody. A Flux source created without a credential, a drift check that only authenticates when a variable happens to be set, a research reader that swallows failure. | `idp/bin/idp-hydrate:16`, `idp/bin/idp-catalogue-drift:57-59`, `crew/science/research_intake.py:56-62` | Make the token mandatory: fail loud when it is absent, never fall back to anonymous. |
| 6 | GitHub's free security features go. Secret scanning, push protection and Dependabot alerts are free on public repositories only. | account-wide | Our own security-scan gate (gitleaks in `idp/.github/actions/security-scan`) stays and is the control; nothing to build. |
| 7 | The merge fence disappears (see above). | idp rulesets | GitHub Pro on the account, before the flip, keeps protected branches and rulesets on private repositories. This is the one thing only the founder can do. |
| 8 | Minutes run out. | every repository | Runners of our own on the cluster, with GitHub's own actions-runner-controller (mature tool; no script). Whether it is needed before the flip is decided by the measured number below. |

## The one order

1. **Founder, one action.** Upgrade the account to GitHub Pro. Without it the flip deletes the
   merge fence, and the "agents never merge" ruling becomes a wish.
2. **Crew, on his word, before the flip.** Land fixes 1 to 5 as one change per repository, each
   green on its own gates while the repositories are still public. Extend
   `~/.claude/scripts/estate/repo_must_be_private.py` from one repository to all nine, so the
   flip has a probe that grades it.
3. **Founder merges** those changes. The fixes are harmless while public.
4. **Flip, in one pass, by API.** `gh repo edit <repo> --visibility private` for every
   repository in the list, from the founder's own login, reported as one line per repository. Then set
   the two Actions access levels (fix 1).
5. **Prove it in the same hour.** The extended probe answers 404 for every repository; one empty
   push to each repository runs its gates green; the catalogue's prospector entry still renders;
   Flux has applied the declared state since the flip; the hourly login drill stays green; the next
   image-update pull request still opens.
6. **New crew.** On a private personal repository a collaborator is invited by API
   (`gh api -X PUT repos/chidionyema/<repo>/collaborators/<login> -f permission=push`), one
   command per person per repository, from the founder's login. No console step, no pasted
   token: the person signs in to GitHub and the estate's App does the rest.

## What is deliberately not in the hours window

- Moving the repositories into an organisation (GitHub Team). It is the shape a buyer expects
  and the shape that gives one place for members, but a transfer rewrites every remote and
  every App installation; it is a planned move, not a flip.
- Making the ghcr packages private. Separate switch, and every area of the cluster that pulls them must
  carry ghcr-pull first (hermes-agent is the one without it).

## Evidence

- Repository list and visibility: `gh repo list chidionyema --json name,visibility`.
- Plan: `gh api repos/chidionyema/estate-secrets/rulesets` answers 403 with the Pro upgrade text.
- Rulesets on idp: `gh api repos/chidionyema/idp/rulesets` lists four, all `active`.
- Deploy keys on idp: `gh api repos/chidionyema/idp/keys` shows the Flux read-only key and flux-writer.
- Actions minutes, last 24 hours, billable, summed over five repositories: see the board comment on
  the tracked item; the script that produced it is quoted there.
- The sweep itself: crew tracked item for this plan, first comment.

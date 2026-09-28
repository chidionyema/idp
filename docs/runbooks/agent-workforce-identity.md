# Runbook: The agent workforce's GitHub identity, and the three ways to stop it

The agent workforce ([its decision record](https://github.com/chidionyema/crew/issues/729)) acts on GitHub as one lane of the estate's one GitHub App,
`estate-agents`. There is no second App, no personal token and no pasted secret. The lane is
named `agent-workforce` in `platform/github-app/lanes.json` and it can do four things: read
repository metadata, push commits to a branch, open and update pull requests, and write
issues. It can also read Actions runs and check results. It can never merge a pull request,
never start a workflow, never change repository settings and never read a secret.

## How the crew gets its token

A token of this lane lives for one hour and is minted fresh each time it is needed. Two ways:

| Where the crew runs | How the token arrives | Who holds the App key |
|---|---|---|
| On the cluster | An `ExternalSecret` beside the workload names a `GithubAccessToken` generator with the lane's six permissions, the same shape as `platform/hermes-agent/gateway.yaml`. External Secrets mints the token on every refresh. | The generator reads the key from the `github-app-pem` secret in its own area of the cluster, rendered from the one vault entry `github-app`. |
| In a GitHub Actions job | `bin/idp-github-app token agent-workforce` prints the token when its output is piped, for example into `gh auth login --with-token`. | The job reads the vault entry `github-app` through `bin/idp-cloud secret get`. |

Both paths narrow the token to the lane's permissions at mint time. A lane never gets more
than the App's own permissions in `platform/github-app/manifest.json`.

## The three kill switches

Every step here is the founder's. No agent performs any of them, and the crew cannot undo any
of them: each one is either a GitHub setting only an owner can change or a change on `main`
that only he merges.

| Switch | What he does | What it stops | What keeps running |
|---|---|---|---|
| 1. Suspend the App | Open https://github.com/settings/installations, find `estate-agents`, press **Suspend**. | Every lane at once: every token of the App stops working within the hour, and no new token can be minted. This is the whole estate's agent access, not only this crew. | Nothing that acts through the App. Flux, the workloads and the cluster are untouched; they only lose their GitHub voice. |
| 2. Delete the lane | Merge one pull request that removes the `agent-workforce` object from `platform/github-app/lanes.json`. | This crew only. `bin/idp-github-app token agent-workforce` answers `REFUSED: no lane 'agent-workforce' in .../lanes.json` and exits 2 before it reads the vault, so no token is minted and no secret is touched. A token minted before the merge dies within the hour. | Every other lane. The other crews, Otto and the alerts writer keep their tokens. |
| 3. Stop the workload | Merge one pull request that sets the crew's `replicas` to `0` in its deployment under `platform/`. | The crew's process. It stops reading its queue and stops acting at all, on GitHub and everywhere else. Flux applies the change the next time it applies the declared state, within a few minutes. | Its identity: the lane is still there, so the founder can bring the crew back with one more pull request and nothing to re-mint. |

Press the switches in the order that matches the worry: a bad actor on the App means
switch 1; a crew that misbehaves means switch 2, then switch 3 to stop it spending compute;
a crew that is merely noisy means switch 3 alone.

## Proof that switch 2 works

`tests/test_crew729_agent_workforce_lane_is_pull_request_only_and_removable.py` runs the script
against a copy of `lanes.json` with the lane removed, with no vault and no network, and reads
the refusal line and the exit code. It also pins the lane's permission set so a later edit
cannot widen it without failing the test.

    python3 -m pytest -q -p no:xdist -o addopts="" tests/test_crew729_agent_workforce_lane_is_pull_request_only_and_removable.py

## How to bring it back

Revert the pull request that pressed the switch. For switch 1, open the same installations
page and press **Unsuspend**. No key is rotated by any of the three switches, so nothing has to
be re-minted by hand.

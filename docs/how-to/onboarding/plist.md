# Onboarding: plist-gate

You touch a launchd template when a job under `launchd/` needs a new key, a different interval or a different command. The gate is what stops a broken edit reaching a machine.

1. Edit `launchd/<label>.plist.tmpl`. Only `${IDP}`, `${HOME}` and `${PATH}` are substituted; every other value is literal (LAW 46: no machine path is typed).
2. Run `python3 bin/plist-gate`. It must print `ok` for every template. A `FAIL` line names the file and the parse error; a `BLIND` exit 2 means it found no templates at all, which is itself a defect.
3. Install with `bin/idp-install-launchd`. It renders, writes to `~/Library/LaunchAgents`, and bootstraps the job. launchd keeps running the definition it loaded last, so an install that is skipped leaves the old job in place.
4. Open the PR. `bin/idp-ci` (the `offline-gate` job) runs the gate both ways and refuses the merge on a template that does not parse.

The gate checks that the rendered file parses, that `Label` and `ProgramArguments` exist, and that `Label` equals the file name. It does not check that the command the job runs exists on the target machine; `bin/idp-verify` grades that after install.

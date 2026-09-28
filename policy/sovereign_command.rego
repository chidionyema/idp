# What a sovereign agent is allowed to run, as policy rather than as an
# `if` in Python.
#
# Spec v1.0 4.2: three models vote, and the winning call must ALSO be
# inside the AGENTS.md allowlist. "If 2/3 agree but the command is outside
# policy -> blocked. Policy is a hard safety invariant above consensus."
# That ordering only means something if the two are separately evaluable,
# which is why this is Rego evaluated by conftest and not a list literal
# next to the voting code: the estate's ruling is that command guards are
# Rego (bin/policy-test, policy/licences.rego, policy/placement.rego), and
# a guard living inside the thing it guards is a guard that ships with
# every bug of its host.
#
# Namespace is `sovereign.command`, NOT `main`. licences.rego and
# placement.rego own `main`; a deny rule of mine in that package would
# fire against their fixtures and break bin/policy-test. Callers pass
# --namespace sovereign.command (sovereign/consensus/policy.py does).
#
# Input, one document per decision:
#
#   {"command": "git status --short", "destructive": true}
#
# deny is the only decision that blocks. A command that matches nothing
# here is denied by the last rule, not allowed: an allowlist that defaults
# to allow is a denylist wearing the wrong name.

package sovereign.command

import rego.v1

# Verbs a sovereign agent may run unattended. Read-only or additive, and
# each one is here because an agent doing its job needs it, not because it
# looked harmless.
allowed_prefixes := {
	"git status",
	"git diff",
	"git log",
	"git add",
	"git commit",
	"git fetch",
	"git branch",
	"git worktree list",
	"ls",
	"cat",
	"head",
	"tail",
	"grep",
	"rg",
	"find",
	"wc",
	"pytest",
	"python -m pytest",
	"make test",
	"kubectl get",
	"kubectl describe",
	"kubectl logs",
	"flux get",
	"docker ps",
	"gh pr view",
	"gh issue view",
}

# Verbs that are refused even when they start with an allowed prefix, and
# even when every model in the estate agrees on them. This set is what
# "policy beats consensus" is made of.
forbidden_fragments := {
	"git push --force",
	"git push -f",
	"git reset --hard",
	"git clean -fdx",
	"rm -rf",
	"mkfs",
	"dd if",
	"drop table",
	"truncate table",
	"delete from",
	"kubectl delete",
	"terraform destroy",
	"fly apps destroy",
	"launchctl bootout",
	"colima stop",
	"colima delete",
	"chmod 777",
	"curl | sh",
	"| sudo",
	"sudo ",
}

command := lower(trim_space(input.command)) if input.command

# A forbidden fragment anywhere in the command blocks it, prefix or no
# prefix. Substring, not prefix: `git status && rm -rf /` starts with an
# allowed prefix and is still the thing this exists to stop.
deny contains msg if {
	some fragment in forbidden_fragments
	contains(command, fragment)
	msg := sprintf("command contains the forbidden fragment %q: %s", [fragment, input.command])
}

allowed_by_prefix if {
	some prefix in allowed_prefixes
	startswith(command, lower(prefix))
}

# Default-deny. Anything the allowlist does not name is refused, which is
# what makes this an allowlist.
deny contains msg if {
	not allowed_by_prefix
	msg := sprintf("command is not in the allowlist: %s", [input.command])
}

# A command with no command in it is not a pass.
deny contains msg if {
	not input.command
	msg := "no command supplied"
}

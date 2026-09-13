# clean-tree: demo

Three defects were reported to the founder in one session. None of them were real.

The shared checkout — the one directory every session on this machine works in — was on another
session's branch with a conflicted merge staged in it. A gate run from there reads that session's
half-written tree:

```
$ cd ~/dev/code/idp && python3 bin/idp-rules run --plane ci
FAIL  live      sleep-ban: every case names a fixture; this rule has never been pointed at the estate
FAIL  coverage  a fixture pair is graded by nothing and is not on the ledger
```

`bin/idp-clean-tree` says why, before any of it is believed:

```
$ bin/idp-clean-tree --path ~/dev/code/idp
FAIL  clean-tree  /Users/chidionyema/dev/code/idp is mid-merge with 1 unmerged file(s) on branch fix/breaker-is-guarded: UU AGENTS.md
      Any gate run here grades a tree that is on nobody's branch. Use a worktree cut from origin/main.
```

A worktree cut from `origin/main` gives the true answer:

```
$ git worktree add /tmp/wt-verify origin/main && cd /tmp/wt-verify
$ python3 bin/idp-rules run --plane ci
$ echo $?
0
```

```
$ python3 bin/idp-rules run --plane ci | grep -c '^ok '
74
```

The three reported defects do not exist on main. The gate is not the problem; the tree was.

An ordinary working tree is not refused — a dirty worktree on a feature branch is how work is done:

```
$ bin/idp-clean-tree --path .
ok    clean-tree  /tmp/wt-verify on fix/some-branch, 3 uncommitted change(s)
```

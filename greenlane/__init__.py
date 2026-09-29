"""Greenlane: the estate's gated trunk. One engine moves main, and only to a commit whose exact
sha passed every required check. Agents never raise a pull request; they push a lane, the engine
proves it, and the pull request is born green and landed in the same act.

`engine.py` is the decision logic, pure and backend-free. `simulate.py` drives it through an
in-memory chaos backend (stale worktrees, broken commits, conflicting lanes, hand-raised PRs,
direct pushes, flaky checks) so the invariants are checked before the code touches GitHub.
`github.py` is the backend that runs in .github/workflows/greenlane.yml. The package sits at
the repository root because `platform` shadows the standard library module of that name.
"""

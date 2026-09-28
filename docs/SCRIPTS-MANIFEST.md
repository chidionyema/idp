# Scripts and Hooks Manifest

**Last updated:** 2026-09-15

## Hooks (2 total)

Defined in `/Users/chidionyema/dev/code/idp/settings.json`

| Hook | Script | Timeout | Purpose |
|------|--------|---------|---------|
| SessionStart | `bin/idp-session-bootstrap` | 120s | Initialize session environment |
| Stop | `bin/idp-reasoning-gateway-hook` | 30s | Grade session with reasoning gateway |

## Scripts

### Bin Directory (310 total)
Located at: `$CLAUDE_PROJECT_DIR/bin/`

**Core IDP scripts (170+):**
- `idp` - Main CLI entry point
- `idp-ci` - CI/CD pipeline runner
- `idp-exec` - Execute commands within idp
- `idp-status`, `idp-up`, `idp-down` - Cluster state management
- `idp-deploy-*` - Deployment utilities
- `idp-session-*` - Session management
- `idp-gate-*` - Gate/policy enforcement
- `idp-proof-*` - Proof verification
- `idp-verify-*` - Verification tools
- And 110+ more in bin/

**Estate scripts (30+):**
- `estate-*` - Estate platform utilities
- `estate-checkpoint`, `estate-cleaner`, `estate-proof`, etc.

**Catalog scripts (10+):**
- `catalog-gen`, `catalog-refcheck`, `catalog-links-check`, etc.

**Utility scripts (40+):**
- `bootstrap-*`, `cloud-agnostic-gate`, `conform-*`, etc.

### Pi Agent Scripts (9 total)
Located at: `~/.pi/agent/scripts/`

| Script | Type | Purpose |
|--------|------|---------|
| `canary.sh` | Shell | Canary testing |
| `edit_workflow.py` | Python | Workflow editor |
| `impl_plan.py` | Python | Implementation planner |
| `incremental.py` | Python | Incremental processing |
| `learning_loop.py` | Python | Learning feedback loop |
| `model_router.py` | Python | Model routing logic |
| `project_context.py` | Python | Project context manager |
| `run-ultimate.sh` | Shell | Ultimate mode runner |
| `test_spec.py` | Python | Specification tester |

## Extensions

### Pi Agent Extensions (7 total)
Located at: `~/.pi/agent/extensions/`

- `breaker` - Circuit breaker logic
- `dispatch` - Task dispatch (symlink to `/private/tmp/idp-router-worktree/extensions/dispatch`)
- `executor-door` - Executor interface
- `feed-guard.ts` - Feed guard (TypeScript)
- `pi-crew` - Crew orchestration
- `pi-delegate` - Delegation handler
- `pi-governance` - Governance rules

## Workflows

### Pi Agent Workflows (7 total)
Located at: `~/.pi/agent/workflows/`

- `pev.yaml` - Preview evaluation workflow
- `probe-devstral-solo.yaml` - Devstral solo probe
- `probe-m3x2.yaml` - M3x2 probe configuration
- `probe-turns.yaml` - Turn-based probe
- `recon.yaml` - Reconnaissance workflow
- `review-fanout.yaml` - Fan-out review workflow
- `ultimate-code.workflow.json` - Ultimate code workflow

## Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| `settings.json` | Repo root | Hooks, pi-agent config, compaction, VCC |
| `pi-vcc-config.json` | `~/.pi/agent/` | Version control context settings |
| `models.json` | `~/.pi/agent/` | Model provider configurations |

## Notes

- All 310 bin scripts are version-controlled in the repository
- Pi agent scripts, extensions, and workflows live in `~/.pi/agent/`
- Two hooks (SessionStart, Stop) are defined in root `settings.json` as single source of truth
- Token management and context pruning configured via `compaction` and `vcc` sections

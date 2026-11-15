# Genesis Zero-Agent Mechanical Lockdown Bundle

This archive contains deterministic, non-agent enforcement artifacts so no LLM agent is ever asked to build or police its own cage:

1. `ruleset-all-branches-lockdown.json`: GitHub Repository Ruleset API payload enforcing:
   - Zero branch or tag deletions across `~ALL` refs (`B5` prevention)
   - Zero force-pushes (`non_fast_forward`)
   - Mandatory cryptographic commit signatures (`B3` prevention)
   - Mandatory GitHub Merge Queue (`ALLGREEN`) with deterministic status checks
2. `.github/workflows/deterministic-zero-agent-cicd.yml`: Pure compiler + static verifier CI/CD pipeline:
   - Explicitly rejects commit `937dda9d` (`B2` `dof-registry` tamper) if present in branch ancestry
   - Blocks any modification to `dof-registry`, `.github/workflows/`, or `catalog/genesis-protocols.json` lacking a Founder Passkey seal
   - Executes `cargo check --workspace --locked` and `cargo test --workspace --locked` with zero LLM calls
3. `.github/CODEOWNERS`: Locks repository control files exclusively to `@chidionyema`.
4. `scripts/enforce_os_agent_eviction.sh`: Local OS eviction script that kills background agent daemons, strips exported `GH_TOKEN` variables from shell rc files, disables Chrome remote debugging (`B4`/`B8`), and cherry-picks only `6ed3d165` onto `origin/main` while dropping `937dda9d`.

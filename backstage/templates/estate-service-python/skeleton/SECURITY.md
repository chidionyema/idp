# Security

Report a vulnerability to the owner named in `catalog-info.yaml`. Every push runs gitleaks,
Trivy, bandit, pip-audit and CodeQL (`.github/workflows/ci.yml`); a finding blocks the merge.

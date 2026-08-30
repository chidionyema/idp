# ${{ values.name }}

${{ values.description }}

Made by the Python golden path (idp `backstage/templates/estate-service-python`). The estate
guards install themselves on the first session (`.claude/settings.json`); the standards are
`pyproject.toml` (ruff, pytest, bandit, pip-audit) and `.github/workflows/ci.yml` runs them with
gitleaks, Trivy and CodeQL on every push. Secrets are files under `/var/run/secrets/${{ values.name }}`.

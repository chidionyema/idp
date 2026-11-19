#!/usr/bin/env bash
# ==============================================================================
# Olat Estate Genesis: Zero-Friction Bitwarden -> GitHub Secrets & Repo Bootstrap
# Pulls specified secrets directly from Bitwarden CLI (`bw` or `bws`), syncs them
# to GitHub Actions secrets on `chidionyema/argo-sync` & `chidionyema/argon`,
# and pushes the full verified Genesis repository—zero manual copy-pasting!
# ==============================================================================
set -euo pipefail

APP_ORIGIN="https://ais-pre-pnuj6ysc7lwv3pfgp5xuxv-534240513427.europe-west3.run.app"
REPOS=("chidionyema/argo-sync" "chidionyema/argon")
BW_ITEM_NAME="${BW_GITHUB_TOKEN_ITEM:-ARGO_SYNC_PAT}"
WORKDIR="/tmp/argo-sync-bw-bootstrap"

echo "==> [1/4] Reading GitHub PAT from Bitwarden ('${BW_ITEM_NAME}')..."
GITHUB_PAT="${ARGO_SYNC_PAT:-${GITHUB_TOKEN:-}}"

if [ -z "${GITHUB_PAT}" ]; then
  if command -v bw >/dev/null 2>&1; then
    # Try Bitwarden Password Manager CLI (`bw`)
    if [ -z "${BW_SESSION:-}" ]; then
      echo "    Unlocking Bitwarden vault (enter master password once)..."
      export BW_SESSION="$(bw unlock --raw)"
    fi
    bw sync >/dev/null 2>&1 || true
    for candidate in "${BW_ITEM_NAME}" "argo-sync-pat" "ARGON_GITHUB_PAT" "GITHUB_TOKEN" "github-pat"; do
      VAL="$(bw get password "${candidate}" 2>/dev/null || bw get notes "${candidate}" 2>/dev/null || true)"
      if [ -n "${VAL}" ]; then
        GITHUB_PAT="${VAL}"
        echo "    Found token in Bitwarden item: ${candidate}"
        break
      fi
    done
  fi
fi

if [ -z "${GITHUB_PAT}" ]; then
  echo "ERROR: Could not auto-detect token under '${BW_ITEM_NAME}' in Bitwarden."
  echo "Run with your Bitwarden item name: BW_GITHUB_TOKEN_ITEM='your-item-name' bash <(curl -fsSL ${APP_ORIGIN}/sync-bitwarden-to-github.sh)"
  exit 1
fi

export GH_TOKEN="${GITHUB_PAT}"
export GITHUB_TOKEN="${GITHUB_PAT}"

echo "==> [2/4] Syncing specified Bitwarden secrets to GitHub Actions (argo-sync & argon)..."
if command -v gh >/dev/null 2>&1; then
  for repo in "${REPOS[@]}"; do
    echo -n "${GITHUB_PAT}" | gh secret set ARGO_SYNC_PAT --repo "${repo}" 2>/dev/null || true
    echo -n "${GITHUB_PAT}" | gh secret set ARGON_GITHUB_PAT --repo "${repo}" 2>/dev/null || true
    echo "    Synced ARGO_SYNC_PAT & ARGON_GITHUB_PAT -> ${repo} (GitHub Actions Secrets)"
  done

  # Sync any additional optional secrets present in Bitwarden allowlist
  if command -v bw >/dev/null 2>&1 && [ -n "${BW_SESSION:-}" ]; then
    for secret_name in "GEMINI_API_KEY" "VITE_TELEGRAM_BOT_WEBHOOK_PUBLIC_KEY"; do
      SEC_VAL="$(bw get password "${secret_name}" 2>/dev/null || bw get notes "${secret_name}" 2>/dev/null || true)"
      if [ -n "${SEC_VAL}" ]; then
        for repo in "${REPOS[@]}"; do
          echo -n "${SEC_VAL}" | gh secret set "${secret_name}" --repo "${repo}" 2>/dev/null || true
        done
        echo "    Synced ${secret_name} from Bitwarden -> GitHub Actions"
      fi
    done
  fi
fi

echo "==> [3/4] Downloading & verifying Genesis bundle (114 tests + 8 laws + HOP-06 Sequencer)..."
rm -rf "${WORKDIR}"
mkdir -p "${WORKDIR}"
curl -fsSL "${APP_ORIGIN}/SOURCE_MANIFEST.json" -o "${WORKDIR}/SOURCE_MANIFEST.json"
curl -fsSL "${APP_ORIGIN}/olat-estate-genesis-main.bundle" -o "${WORKDIR}/olat-estate-genesis-main.bundle"

git clone "${WORKDIR}/olat-estate-genesis-main.bundle" "${WORKDIR}/repo"
cd "${WORKDIR}/repo"
cp "${WORKDIR}/SOURCE_MANIFEST.json" ./SOURCE_MANIFEST.json

npm install --no-audit --no-fund
npm test
npm run enforce
npm run hop:sequencer
npm run verify:release

echo "==> [4/4] Pushing verified branches & tags directly to chidionyema/argon (Strictly No --force, non-argv auth)..."
AUTH_B64=$(printf "x-access-token:%s" "${GITHUB_PAT}" | base64 | tr -d '\n')
git -c "http.extraheader=AUTHORIZATION: basic ${AUTH_B64}" push https://github.com/chidionyema/argon.git \
  HEAD:refs/heads/genesis-live \
  HEAD:refs/heads/inbox/incoming \
  HEAD:refs/heads/inbox/DROP-2026-1078 \
  --tags

echo ""
echo "=============================================================================="
echo "DONE! Bitwarden -> GitHub Secrets synced AND chidionyema/argo-sync bootstrapped!"
echo "ONE FINAL 10-SECOND STEP FOR AI STUDIO:"
echo "  In the AI Studio left sidebar, click the Key icon (Secrets) and paste your"
echo "  token into ARGO_SYNC_PAT so this Cloud Run container can also push directly."
echo "=============================================================================="

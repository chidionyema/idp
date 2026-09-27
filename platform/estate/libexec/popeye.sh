#!/usr/bin/env bash
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
if ! command -v popeye >/dev/null 2>&1; then
  echo "popeye not installed. Install: brew install derailed/popeye/popeye"
  echo "Or: curl -sL https://github.com/derailed/popeye/releases/latest/download/popeye_$(uname -s)_$(uname -m).tar.gz | tar xz -C /tmp && sudo mv /tmp/popeye /usr/local/bin/"
  exit 0
fi
K="${K:-$HOME/.kube/oke-direct}"
popeye --kubeconfig "$K" --min-score "${POPEYE_MIN:-80}" --save --output wide 2>&1 | tail -60

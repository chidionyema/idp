#!/usr/bin/env bash
# Freeze new or modified operational prose; deletion remains possible for migration.
set -euo pipefail
shopt -s nocasematch
is_operational_prose() {
  local path=$1 name=${1##*/}
  # Only these dedicated namespaces are exceptions. They are not operational authority.
  case "$path" in
    corporate/*|vision/*|docs/marketing/*|docs/vision/*) return 1 ;;
  esac
  case "$name" in
    LICENSE|LICENSE.*|LICENCE|LICENCE.*|NOTICE|NOTICE.*|COPYING|COPYING.*) return 1 ;;
    AGENTS|AGENTS.*|CLAUDE|CLAUDE.*|GEMINI|GEMINI.*|README|README.*|RUNBOOK|RUNBOOK.*|CHANGELOG|CHANGELOG.*|CONTRIBUTING|CONTRIBUTING.*) return 0 ;;
    *.md|*.mdx|*.markdown|*.rst|*.adoc|*.asciidoc|*.org|*.pdf|*.doc|*.docx) return 0 ;;
  esac
  case "$path" in
    docs/*.txt|docs/*.html|*/docs/*.txt|*/docs/*.html|runbooks/*.txt|*/runbooks/*.txt|documentation/*.txt|*/documentation/*.txt) return 0 ;;
  esac
  return 1
}
if [ "${1:-}" = --self-test ]; then
  for path in AGENTS.md src/README CLAUDE.MD docs/ops/status.txt docs/runbooks/incident.html src/note.rst src/design.pdf; do
    if ! is_operational_prose "$path"; then echo "FAIL expected refusal: $path"; exit 1; fi
  done
  for path in src/main.rs Cargo.toml requirements.txt docs/trace-matrix.json LICENSE third_party/NOTICE.md corporate/overview.md vision/mission.md docs/marketing/index.md; do
    if is_operational_prose "$path"; then echo "FAIL expected admission: $path"; exit 1; fi
  done
  echo 'operational-prose self-test: 16/16 passed'
  exit 0
fi
if [ "$#" -ne 2 ]; then echo 'usage: operational-prose-gate.sh BASE HEAD' >&2; exit 2; fi
base=$1
head=$2
# Resolve both before diffing; a missing base is not a successful empty scan.
git rev-parse --verify "$base^{commit}" >/dev/null
git rev-parse --verify "$head^{commit}" >/dev/null
list=$(mktemp)
trap 'rm -f "$list"' EXIT
git diff --no-renames --name-only --diff-filter=AMT -z "$base" "$head" -- > "$list"
git diff --cached --no-renames --name-only --diff-filter=AMT -z -- >> "$list"
failed=0
while IFS= read -r -d '' path; do
  if is_operational_prose "$path"; then
    printf 'FAIL operational prose mutation: %q\n' "$path"
    failed=1
  fi
done < "$list"
if [ "$failed" -ne 0 ]; then exit 1; fi
echo 'operational-prose: no forbidden additions or modifications'

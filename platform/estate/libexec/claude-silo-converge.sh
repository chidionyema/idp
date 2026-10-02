#!/bin/bash
# claude-silo-converge: no estate knowledge lives in a Claude-only folder. Ever. Unattended.
#
# WHY. The estate is model-agnostic (AGENTS.md R6): pi, opencode, Cursor, Cline and Claude Code
# all work it, and every one of them reads AGENTS.md, the growmos graph, ~/.estate and crew.
# Anything written instead into ~/.claude (AGENTS.md copies and snapshots, agents/, skills/,
# plans/, research/, docs/, directives/, settings.json.bak-*) or a repository's .claude/
# (skills, settings, EnterWorktree's worktrees/) is seen by one model only: the next model starts
# from a different world. Founder 2026-09-29: "siloing information and causing split brain ...
# this is a hostile act"; "how many times have we gutted this folder only for it to rear its ugly
# head again". CI already refuses .claude/ in a commit (#4722); nothing kept the LOCAL folders
# converged, so they regrew from agents, hooks and Claude Code itself. This runs every five
# minutes from bin/idp-disk-watch, so the folder cannot stay wrong for longer than that.
#
# WHAT. ~/.claude keeps exactly Claude Code's own runtime state (KEEP below: settings.json, the
# projects/ transcripts and auto-memory, sessions, history, caches, plugins, mcp, telemetry).
# Everything else under ~/.claude, and every <repo>/.claude directory in an estate repository,
# is MOVED to ~/.estate/quarantine/claude/<utc-stamp>/ -- never deleted on the spot, so a wrong
# match costs nothing -- and quarantine older than KEEP_DAYS is removed, so the quarantine is
# self-bounding (no cap, no alert, no maintenance). Worktrees under <repo>/.claude/worktrees
# are detached with `git worktree remove` when settled (clean, no lock); a dirty one is left
# and named, never forced. One line per action to ~/.estate/claude-silo.log.
#
#   claude-silo-converge.sh [--dry-run]

set -uo pipefail
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
HOME_DIR="${HOME:?}"
CLAUDE="$HOME_DIR/.claude"
Q_ROOT="$HOME_DIR/.estate/quarantine/claude"
LOG="$HOME_DIR/.estate/claude-silo.log"
KEEP_DAYS="${CLAUDE_SILO_KEEP_DAYS:-14}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
Q="$Q_ROOT/$STAMP"
# Claude Code's own runtime state. Names, not patterns: an entry not listed here is a silo.
KEEP="settings.json projects sessions history.jsonl cache plugins mcp telemetry shell-snapshots file-history paste-cache debug downloads statsig todos ide backups .credentials.json .DS_Store"
REPOS="${CLAUDE_SILO_REPOS:-$HOME_DIR/Documents/code/idp $HOME_DIR/Documents/code/crew $HOME_DIR/Documents/code/estate-core $HOME_DIR/Documents/code/estate-graph $HOME_DIR/Documents/code/estate-secrets}"

moved=0
say() { echo "$(date -u +%FT%TZ) $*" >>"$LOG"; echo "$*"; }
quarantine() { # $1 = absolute path, $2 = label
	local rel="$2"
	if [ "$DRY" = 1 ]; then say "would-move $1 -> quarantine/$rel"; return; fi
	mkdir -p "$Q/$(dirname "$rel")" && mv "$1" "$Q/$rel" && { moved=$((moved + 1)); say "moved     $1 -> $Q/$rel"; }
}

# 1. ~/.claude: everything not in KEEP is a silo.
if [ -d "$CLAUDE" ]; then
	for p in "$CLAUDE"/* "$CLAUDE"/.[!.]*; do
		[ -e "$p" ] || continue
		n=$(basename "$p")
		case " $KEEP " in *" $n "*) continue ;; esac
		quarantine "$p" "home/$n"
	done
fi

# 2. <repo>/.claude: worktrees detached when settled, then the directory itself.
for r in $REPOS; do
	d="$r/.claude"
	[ -d "$d" ] || continue
	if [ -d "$d/worktrees" ]; then
		for w in "$d"/worktrees/*; do
			[ -d "$w" ] || continue
			if [ -f "$w/.git" ] || [ -d "$w/.git" ]; then
				if [ -z "$(git -C "$w" status --porcelain 2>/dev/null)" ] && [ ! -f "$w/.git/locked" ]; then
					if [ "$DRY" = 1 ]; then say "would-remove worktree $w"; else
						git -C "$r" worktree remove "$w" >/dev/null 2>&1 && say "removed   worktree $w" || say "kept      worktree $w (git refused; not forced)"
					fi
				else
					say "kept      worktree $w (dirty or locked; not forced)"
				fi
			else
				quarantine "$w" "$(basename "$r")/worktrees/$(basename "$w")"
			fi
		done
		[ "$DRY" = 1 ] || rmdir "$d/worktrees" 2>/dev/null
	fi
	for p in "$d"/* "$d"/.[!.]*; do
		[ -e "$p" ] || continue
		quarantine "$p" "$(basename "$r")/$(basename "$p")"
	done
	[ "$DRY" = 1 ] || rmdir "$d" 2>/dev/null
	[ -d "$d" ] && [ "$DRY" = 0 ] && say "kept      $d (not empty after converge)"
done

# 3. The quarantine bounds itself.
if [ -d "$Q_ROOT" ] && [ "$DRY" = 0 ]; then
	find "$Q_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$KEEP_DAYS" -exec rm -rf {} + 2>/dev/null
	rmdir "$Q" 2>/dev/null
fi
[ "$moved" -gt 0 ] && say "ok        claude-silo  $moved item(s) quarantined to $Q (kept $KEEP_DAYS days)"
exit 0

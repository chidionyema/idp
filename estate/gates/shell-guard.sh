# estate api-port-guard -- shell layer, harness-agnostic (Claude Code, Codex, OpenCode, DSH, pi).
#
# A PreToolUse hook protects one harness; the shell is where every harness's command runs.
# `kill` is a builtin, so a PATH shim never sees it: these functions shadow the verbs, ask the
# judge (api-port-guard --argv, which sees the EXPANDED argv), then run the real command.
# Sourced from ~/.zshenv (every zsh) and BASH_ENV (every non-interactive bash).
#
# Only a verdict refuses: the judge exits 2. Any other status -- python missing, a crash, a
# timeout -- runs the real command, because a shell that stops working is the outage itself.
# Cheap paths never start python: kill -0 / -l and launchctl print/list/getenv/....

ESTATE_GUARD="${ESTATE_GUARD:-$HOME/.estate/hooks/api-port-guard}"

_estate_guard() {
    [ -r "$ESTATE_GUARD" ] || return 0
    /usr/bin/python3 -I "$ESTATE_GUARD" --argv "$@"
    [ $? -ne 2 ]
}

kill() {
    case "${1-}" in
        -0|-SIG0|-l|-L) builtin kill "$@"; return ;;
        -s|-n) [ "${2-}" = 0 ] && { builtin kill "$@"; return; } ;;
    esac
    _estate_guard kill "$@" || return 1
    builtin kill "$@"
}

pkill() { _estate_guard pkill "$@" || return 1; command -p pkill "$@"; }
killall() { _estate_guard killall "$@" || return 1; command -p killall "$@"; }

launchctl() {
    case "${1-}" in
        bootout|unload|remove|stop|kill|kickstart) _estate_guard launchctl "$@" || return 1 ;;
    esac
    command -p launchctl "$@"
}

systemctl() {
    case " $* " in
        *" stop "*|*" kill "*|*" restart "*|*" disable "*|*" mask "*) _estate_guard systemctl "$@" || return 1 ;;
    esac
    command -p systemctl "$@"
}

# estate zero-worktree -- the MacBook is a stateless thin client (founder executive order
# 2026-11-11; platform/estate/governance/thin_client.py). `git worktree add` and `git clone`
# build a full local checkout, so the door asks the existing judge (bin/estate-zero-worktree
# check, exit 78 = refused). Same failure policy as the kill guard: only a verdict refuses;
# a missing judge, a crash or BLIND runs the real command. Cheap path: every other git
# subcommand never starts python.
_estate_zw() {
    local _z="${ESTATE_ZERO_WORKTREE:-$HOME/Documents/code/idp/bin/estate-zero-worktree}"
    [ -r "$_z" ] || return 0
    /usr/bin/python3 -I "$_z" check -- "$@" >&2
    [ $? -ne 78 ]
}

git() {
    local _sub="" _skip=0 _x
    for _x in "$@"; do
        if [ "$_skip" = 1 ]; then _skip=0; continue; fi
        case "$_x" in
            -C|-c|--git-dir|--work-tree|--namespace|--exec-path) _skip=1 ;;
            -*) ;;
            *) _sub="$_x"; break ;;
        esac
    done
    case "$_sub" in
        clone) _estate_zw git "$@" || return 1 ;;
        worktree) case " $* " in *" add "*) _estate_zw git "$@" || return 1 ;; esac ;;
    esac
    command git "$@"
}

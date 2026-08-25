"""otto.* / telegram.* configurable keys — cp22 "everything configurable".

Every numeric literal (other than 0/1/-1) and path/URL string literal used
by sovereign/otto/ lives here, named, with a default, a type, an env var
name and one line of help — never as a bare literal in card.py, cli.py or
hermes_plugin/__init__.py. See features/sovereign-bus/cp22_everything_configurable.feature
and CONTRACT.md's Config section.

Shape agreed with builder A: OTTO_KEYS: {key: (default, type, env_name,
help)}. sovereign/config.py imports this module and merges OTTO_KEYS into
its own KEYS table for `sb config --lint`/introspection. This module does
not depend on sovereign.config existing — get() resolves env-or-default on
its own, so otto/ works standalone before or after the merge.
"""

from __future__ import annotations

import os
from typing import Any

# {key: (default, type, env_name, help)}
OTTO_KEYS: dict[str, tuple[Any, type, str, str]] = {
    "telegram.api_base": (
        "https://api.telegram.org", str, "TELEGRAM_API_BASE",
        "Telegram Bot API base URL"),
    "telegram.request_timeout_s": (
        5, float, "TELEGRAM_REQUEST_TIMEOUT_S",
        "Total (connect+read+write+pool) timeout in seconds for one Telegram "
        "Bot API call; must stay <=5s so a hung call cannot stall the caller's "
        "event loop / activity"),
    "telegram.parse_mode": (
        "HTML", str, "TELEGRAM_PARSE_MODE",
        "Telegram parse_mode for card and line messages"),

    "otto.task_max_chars": (
        40, int, "OTTO_TASK_MAX_CHARS",
        "Max chars of a session's task shown on the card"),
    "otto.time_format": (
        "%H:%M", str, "OTTO_TIME_FORMAT",
        "strftime format for the card header and per-line timestamps"),
    "otto.done_today_window_hours": (
        24, int, "OTTO_DONE_TODAY_WINDOW_HOURS",
        "Hours a finished session still counts toward 'Done today'"),
    "otto.card_max_button_rows": (
        8, int, "OTTO_CARD_MAX_BUTTON_ROWS",
        "Max session buttons shown under the pinned card"),
    "otto.session_id_display_chars": (
        8, int, "OTTO_SESSION_ID_DISPLAY_CHARS",
        "Chars of a session id shown in chat or plugin output"),
    "otto.json_indent": (
        2, int, "OTTO_JSON_INDENT",
        "Indent width for otto.json"),

    "otto.card_header_template": (
        "\U0001f4cc ESTATE · {time}", str, "OTTO_CARD_HEADER_TEMPLATE",
        "Card header line; {time}"),
    "otto.card_counts_template": (
        "Running {running} · Waiting on you {waiting} · Done today {done}",
        str, "OTTO_CARD_COUNTS_TEMPLATE", "Card counts line"),
    "otto.line_running_template": (
        "▶ {repo} · {task} — step {step}", str,
        "OTTO_LINE_RUNNING_TEMPLATE", "Per-session line while running"),
    "otto.line_waiting_template": (
        "⏸ {repo} · {task} — needs: {asking}", str,
        "OTTO_LINE_WAITING_TEMPLATE", "Per-session line while waiting"),
    "otto.line_done_template": (
        "✔ {repo} · {task} · done {time}", str,
        "OTTO_LINE_DONE_TEMPLATE", "Collapsed line when a session finishes"),
    "otto.line_stopped_template": (
        "\U0001f6d1 {repo} · {task} · stopped {time}", str,
        "OTTO_LINE_STOPPED_TEMPLATE", "Collapsed line when a session is stopped"),
    "otto.line_denied_template": (
        "❌ {repo} · {task} · denied {time}", str,
        "OTTO_LINE_DENIED_TEMPLATE", "Collapsed line when a session is denied"),
    "otto.line_failed_template": (
        "⚠️ {repo} · {task} · failed {time}", str,
        "OTTO_LINE_FAILED_TEMPLATE", "Collapsed line when a session fails"),
    "otto.line_fallback_template": (
        "{repo} · {task}", str, "OTTO_LINE_FALLBACK_TEMPLATE",
        "Line used for an unrecognized status"),
    "otto.footer_cockpit_url_template": (
        "Cockpit: {url}", str, "OTTO_FOOTER_COCKPIT_URL_TEMPLATE",
        "Card footer when ESTATE_PUBLIC_URL is set"),
    "otto.footer_laptop_only": (
        "Cockpit: laptop only", str, "OTTO_FOOTER_LAPTOP_ONLY",
        "Card footer when no public URL is configured"),
    "otto.footer_command_hints": (
        "/sb_stop &lt;id&gt; · /sb_approve &lt;id&gt; · "
        "/sb_deny &lt;id&gt; · /sb_steer &lt;id&gt; &lt;text&gt;",
        str, "OTTO_FOOTER_COMMAND_HINTS",
        "Plain command hints appended to the card when no public URL"),
    "otto.button_label_template": (
        "{sid} →", str, "OTTO_BUTTON_LABEL_TEMPLATE",
        "Inline web_app button label"),
    "otto.button_url_template": (
        "{url}/s/{sid}", str, "OTTO_BUTTON_URL_TEMPLATE",
        "Inline web_app button URL, relative to ESTATE_PUBLIC_URL"),

    "otto.estate_env_relpath": (
        ".config/estate/estate.env", str, "OTTO_ESTATE_ENV_RELPATH",
        "Path under $HOME to the estate credentials file"),
    "otto.default_estate_home_dirname": (
        ".estate", str, "OTTO_DEFAULT_ESTATE_HOME_DIRNAME",
        "Fallback $ESTATE_HOME dirname under $HOME"),

    "otto.plugin_sb_timeout_s": (
        30, float, "OTTO_PLUGIN_SB_TIMEOUT_S",
        "Timeout in seconds for the hermes plugin's `sb ...` subprocess"),
    "otto.plugin_reply_max_lines": (
        6, int, "OTTO_PLUGIN_REPLY_MAX_LINES",
        "Max lines a plugin command reply may contain"),
    "otto.plugin_list_task_max_chars": (
        30, int, "OTTO_PLUGIN_LIST_TASK_MAX_CHARS",
        "Task chars shown per row in sb-list"),
    "otto.plugin_show_task_max_chars": (
        60, int, "OTTO_PLUGIN_SHOW_TASK_MAX_CHARS",
        "Task chars shown in sb-show"),
    "otto.plugin_show_output_max_chars": (
        80, int, "OTTO_PLUGIN_SHOW_OUTPUT_MAX_CHARS",
        "last_output chars shown in sb-show"),
    "otto.plugin_error_max_chars": (
        500, int, "OTTO_PLUGIN_ERROR_MAX_CHARS",
        "Max chars of an sb error surfaced to chat"),
    "otto.plugin_steer_min_parts": (
        2, int, "OTTO_PLUGIN_STEER_MIN_PARTS",
        "Min whitespace-split parts required by /sb-steer (id + text)"),

    "otto.hermes_home_default_dirname": (
        ".hermes", str, "OTTO_HERMES_HOME_DEFAULT_DIRNAME",
        "Fallback $HERMES_HOME dirname under $HOME"),
    "otto.hermes_gateway_plist_relpath": (
        "Library/LaunchAgents/ai.architect.gateway.plist", str,
        "OTTO_HERMES_GATEWAY_PLIST_RELPATH",
        "Path under $HOME to the hermes gateway launchd plist, read for its HERMES_HOME"),
    "otto.hermes_plugin_link_name": (
        "sovereign", str, "OTTO_HERMES_PLUGIN_LINK_NAME",
        "Name of the symlink created under $HERMES_HOME/plugins/"),

    "otto.iso_utc_offset": (
        "+00:00", str, "OTTO_ISO_UTC_OFFSET",
        "Offset substituted for a trailing 'Z' when parsing an ISO timestamp"),
    "otto.cli_card_reset_help": (
        "Forget otto.json (does not unpin/delete in Telegram)", str,
        "OTTO_CLI_CARD_RESET_HELP", "--help text for `sb card-reset`"),
    "otto.cli_install_plugin_help": (
        "Symlink the hermes-agent plugin into $HERMES_HOME/plugins", str,
        "OTTO_CLI_INSTALL_PLUGIN_HELP", "--help text for `sb install-plugin`"),
    "otto.plugin_usage_id_template": (
        "usage: /{cmd} <id>", str, "OTTO_PLUGIN_USAGE_ID_TEMPLATE",
        "Usage message for id-only plugin commands (show/stop/approve/deny)"),
    "otto.plugin_usage_steer": (
        "usage: /sb-steer <id> <text>", str, "OTTO_PLUGIN_USAGE_STEER",
        "Usage message for /sb-steer"),
}


def get(key: str) -> Any:
    """Resolve one otto.*/telegram.* key: env override, else the default.

    Standalone by design (does not require sovereign.config to exist or to
    have merged OTTO_KEYS yet) — see module docstring.
    """
    default, typ, env_name, _help = OTTO_KEYS[key]
    raw = os.environ.get(env_name)
    if raw is None:
        return default
    if typ is bool:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    try:
        return typ(raw)
    except (TypeError, ValueError):
        return default

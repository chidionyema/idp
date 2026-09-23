"""intake.* configurable keys -- cp22 "everything configurable".

Same shape as sovereign/consensus/config_keys.py: {key: (default, type,
env_name, help)}, merged into config.py's KEYS table by _merge_external_keys.
Standalone get() so this package never imports sovereign.config at module
load, which keeps the pipeline importable from a hermes-v2 handler that only
has the sovereign package on its path.

Not redeclared here: model.vision (SB_MODEL_VISION) already lives in
config.py. intake.vision_model (SB_VISION_MODEL, the name the cp25 feature
uses) overrides it when set and falls back to it when not, so both env names
name the same LiteLLM alias and neither is a model name.
"""
from __future__ import annotations

import os
from typing import Any

INTAKE_KEYS: dict[str, tuple[Any, type, str, str]] = {
    "intake.vision_model": (
        "", str, "SB_VISION_MODEL",
        "LiteLLM alias for the vision-to-repo pipeline (spec 2.3). Empty means "
        "use model.vision. An alias, never a provider model name (R8)"),
    "intake.docs_dir": (
        "docs", str, "SB_INTAKE_DOCS_DIR",
        "Directory inside the target repo an intake file is committed under"),
    "intake.file_suffix": (
        ".md", str, "SB_INTAKE_FILE_SUFFIX",
        "Suffix of the committed markdown file"),
    "intake.slug_words": (
        3, int, "SB_INTAKE_SLUG_WORDS",
        "Words the model is asked to put in the filename slug (spec 2.3 step 2)"),
    "intake.tag_count": (
        3, int, "SB_INTAKE_TAG_COUNT",
        "Keyword tags the model is asked to extract (spec 2.3 step 2)"),
    "intake.slug_max_len": (
        60, int, "SB_INTAKE_SLUG_MAX_LEN",
        "Hard cap on the sanitized slug, so a runaway model cannot name a 4 KB file"),
    "intake.op_name": (
        "doc_commit", str, "SB_INTAKE_OP_NAME",
        "The op the governance kernel classifies an intake write as; listed in "
        "ops.nondestructive so no quorum is needed (spec 2.3 step 3)"),
    "intake.receipt_kind": (
        "doc_commit", str, "SB_INTAKE_RECEIPT_KIND",
        "kind field on the receipt line an intake appends"),
    "intake.receipt_tag": (
        "DOC_COMMIT", str, "SB_INTAKE_RECEIPT_TAG",
        "The upper-case word after the tick in the one-line receipt (spec 2.3 step 4)"),
    "intake.hash_short_len": (
        8, int, "SB_INTAKE_HASH_SHORT_LEN",
        "Characters of the commit hash shown in the receipt line"),
    "intake.timeout_s": (
        300, float, "SB_INTAKE_TIMEOUT_S",
        "httpx timeout for one vision call through the LiteLLM proxy"),
    "intake.git_timeout_s": (
        30, float, "SB_INTAKE_GIT_TIMEOUT_S",
        "Timeout on one git subprocess call made while committing"),
    "intake.max_tokens": (
        4096, int, "SB_INTAKE_MAX_TOKENS",
        "Completion cap for one extraction; a page of text fits, a book does not"),
    "intake.temperature": (
        0, float, "SB_INTAKE_TEMPERATURE",
        "Sampling temperature for extraction -- 0, because the output is a transcript"),
    "intake.image_mime_default": (
        "image/jpeg", str, "SB_INTAKE_IMAGE_MIME_DEFAULT",
        "MIME type assumed when the caller does not say; Telegram photos are JPEG"),
    "intake.image_data_url_prefix": (
        "data:", str, "SB_INTAKE_IMAGE_DATA_URL_PREFIX",
        "Scheme prefix of the inline image URL sent in the OpenAI-shaped vision message"),
    "intake.image_data_url_encoding": (
        ";base64,", str, "SB_INTAKE_IMAGE_DATA_URL_ENCODING",
        "Encoding marker between the MIME type and the payload of the inline image URL"),
    "intake.system_prompt": (
        "You are an extraction tool. Extract all text in the image cleanly. "
        "Format it as semantic Markdown. Return one JSON object and nothing else, "
        "with exactly these keys -- \"markdown\" (the formatted text), "
        "\"slug\" (a {slug_words}-word lower-case filename slug), "
        "\"tags\" (a list of {tag_count} keyword tags), \"title\" (one line). "
        "Never reply with prose. Never echo the text outside the JSON.",
        str, "SB_INTAKE_SYSTEM_PROMPT",
        "The strict JSON system prompt (spec 2.3 step 2). {slug_words} and "
        "{tag_count} are filled from the keys above"),
    "intake.session_id": (
        "intake", str, "SB_INTAKE_SESSION_ID",
        "session_id stamped on an intake receipt when the caller has no session"),
    "intake.runner_name": (
        "intake", str, "SB_INTAKE_RUNNER_NAME",
        "runner field on an intake receipt"),
    "intake.commit_prefix": (
        "intake", str, "SB_INTAKE_COMMIT_PREFIX",
        "First word of the git commit subject for a committed document"),
    "intake.laptop_source_name": ("laptop", str, "SB_INTAKE_LAPTOP_SOURCE", "source label for the laptop entry point"),
    "intake.phone_source_name": ("phone", str, "SB_INTAKE_PHONE_SOURCE", "source label for the phone entry point"),
    "intake.chat_source_name": ("chat", str, "SB_INTAKE_CHAT_SOURCE", "source label for the chat entry point"),
    "intake.cli_channel": ("cli", str, "SB_INTAKE_CLI_CHANNEL", "channel the CLI's one-line receipt is printed as"),
    "intake.converse_state_name": (
        "converse", str, "SB_INTAKE_CONVERSE_STATE_NAME",
        "The presence state intake must never move the founder into (R4)"),
}


def get(key: str) -> Any:
    default, typ, env_name, _help = INTAKE_KEYS[key]
    raw = os.environ.get(env_name)
    if raw is None:
        return default
    if typ is bool:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    try:
        return typ(raw)
    except (TypeError, ValueError):
        return default

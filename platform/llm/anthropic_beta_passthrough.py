"""Forward every client `anthropic-beta` value AND every request field to Anthropic unchanged
on the `claude-*` lane.

WHY (measured 2026-09-26, LiteLLM 1.98.0 on the laptop router). LiteLLM allow-lists beta
values: `anthropic_beta_headers_manager.filter_and_transform_beta_headers` drops any value that
is not a key in its JSON map, which it fetches from BerriAI's GitHub at startup. Claude Code
ships betas faster than that map moves -- `inline-tools-2026-09-15` was in neither the bundled
map (29 entries) nor the remote one (33), so a real Opus turn through the router got

    400 messages.1.content.1: `tool_addition` blocks require anthropic-beta: inline-tools-2026-09-15

(request_id req_011CfS9jvN3PuvMhUBVz8cnD). The map exists to translate betas for Bedrock and
Vertex, which name them differently. For direct Anthropic there is nothing to translate: the
client that wrote the request is the authority on which betas it needs, and the lane is a
passthrough of the client's own OAuth token already.

HOW. Loaded as a LiteLLM callback (`anthropic_beta_passthrough.proxy_handler_instance`), so
importing it happens at proxy start. It replaces the module-level function in place, which is
what `update_headers_with_filtered_beta` resolves at call time. Provider "anthropic" gets the
client's values, de-duplicated; every other provider still goes through LiteLLM's own map.

REQUEST FIELDS, the same defect one layer down (measured 2026-09-26). LiteLLM also allow-lists
top-level /v1/messages fields -- `AnthropicMessagesRequestUtils.get_requested_anthropic_messages_
optional_param` keeps only the keys of its `AnthropicMessagesRequestOptionalParams` TypedDict --
and silently dropped Claude Code's `safeguards` field from every main-loop request. Without it
the server-side tool-safety verdict never comes back, so Claude Code falls back to calling its
auto-mode classifier itself, and that call 429'd on the Max token five retries in a row: every
Bash call in auto mode was refused ("blocked by a temporary rate limit on the safety
classifier"). Measured on the same prompt: direct and through a plain byte forwarder, zero
classifier calls and Bash ran; through LiteLLM, the classifier was called and 429'd 75 times.
For provider "anthropic" the patch below adds back every top-level field the client actually
sent that LiteLLM does not handle itself, so the next field Claude Code ships is not lost too.
"""

import inspect
import logging

from litellm import anthropic_beta_headers_manager as _mgr
from litellm.llms.anthropic.experimental_pass_through.messages import utils as _utils
from litellm.integrations.custom_logger import CustomLogger

log = logging.getLogger("estate.anthropic-beta-passthrough")

_original = getattr(
    _mgr.filter_and_transform_beta_headers,
    "__wrapped__",
    _mgr.filter_and_transform_beta_headers,
)


def filter_and_transform_beta_headers(beta_headers, provider):
    if _mgr.get_provider_name(provider) != "anthropic":
        return _original(beta_headers, provider)
    return sorted({h.strip() for h in beta_headers or [] if h and h.strip()})


filter_and_transform_beta_headers.__wrapped__ = _original
_mgr.filter_and_transform_beta_headers = filter_and_transform_beta_headers
log.info("anthropic-beta passthrough active for provider=anthropic")

# Top-level body fields LiteLLM carries itself (outside the optional params); never re-added.
_HANDLED_ELSEWHERE = frozenset(
    {"model", "messages", "stream", "metadata", "max_tokens"}
)
_original_params = (
    _utils.AnthropicMessagesRequestUtils.get_requested_anthropic_messages_optional_param
)
# The router pins 1.98.0, whose signature takes model/drop_params/custom_llm_provider; CI's
# python3 carries 1.83.9, which takes no `model` (TypeError, 2026-09-26). Pass on only what the
# installed version accepts.
_original_kw = frozenset(inspect.signature(_original_params).parameters)


def get_requested_anthropic_messages_optional_param(params, **kw):
    out = _original_params(params, **{k: v for k, v in kw.items() if k in _original_kw})
    if kw.get("custom_llm_provider") != "anthropic":
        return out
    body = ((params or {}).get("proxy_server_request") or {}).get("body") or {}
    for k, v in body.items():
        # litellm_* are the proxy's own keys, written into the same dict (measured 2026-09-26)
        if k in out or k in _HANDLED_ELSEWHERE or k.startswith("litellm_") or v is None:
            continue
        # the value after pre-call hooks if one rewrote it, else what the client sent
        out[k] = params.get(k, v)
    return out


_utils.AnthropicMessagesRequestUtils.get_requested_anthropic_messages_optional_param = (
    staticmethod(get_requested_anthropic_messages_optional_param)
)


class AnthropicBetaPassthrough(CustomLogger):
    """No hooks: the import above is the whole effect. A class only so LiteLLM can load it."""


proxy_handler_instance = AnthropicBetaPassthrough()

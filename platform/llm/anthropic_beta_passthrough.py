"""Forward every client `anthropic-beta` value to Anthropic unchanged on the `claude-*` lane.

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
"""

import logging

from litellm import anthropic_beta_headers_manager as _mgr
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


class AnthropicBetaPassthrough(CustomLogger):
    """No hooks: the import above is the whole effect. A class only so LiteLLM can load it."""


proxy_handler_instance = AnthropicBetaPassthrough()

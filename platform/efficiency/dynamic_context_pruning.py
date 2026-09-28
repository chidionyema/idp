#!/usr/bin/env python3
"""Dynamic context pruning: compress, deduplicate, prune conversation context."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DynamicContextPruning:
    """Automatically manage context size with compression and deduplication."""

    def __init__(self, max_context_pct: float = 0.8, min_context_pct: float = 0.4):
        self.max_context_pct = max_context_pct
        self.min_context_pct = min_context_pct
        self.compressions: int = 0
        self.deduplicates: int = 0
        self.tokens_saved: int = 0

    def deduplicate_tool_outputs(self, conversation: list) -> list:
        """Remove duplicate tool outputs (same tool, same args)."""
        seen_calls = {}
        deduplicated = []

        for msg in conversation:
            if msg.get("type") == "tool_call":
                call_key = f"{msg.get('tool')}:{msg.get('args_hash', '')}"

                if call_key in seen_calls:
                    self.deduplicates += 1
                    self.tokens_saved += len(str(msg.get("result", ""))) // 4
                    logger.info(f"[DCP] Deduplicated {call_key}, saved tokens")
                    continue

                seen_calls[call_key] = msg

            deduplicated.append(msg)

        return deduplicated

    def compress_stale_ranges(
        self, conversation: list, stale_threshold: int = 5
    ) -> list:
        """Replace stale conversation ranges with technical summary."""
        if len(conversation) < stale_threshold:
            return conversation

        stale_range = conversation[:-stale_threshold]
        recent_range = conversation[-stale_threshold:]

        summary = f"[COMPRESSED: {len(stale_range)} prior exchanges summarized]\n"
        summary += (
            f"Context: Agent working on goal. Completed {len(stale_range)} steps."
        )

        self.compressions += 1
        self.tokens_saved += len(str(stale_range)) // 4 - len(summary) // 4

        logger.info(f"[DCP] Compressed stale range, saved ~{self.tokens_saved} tokens")

        return [{"type": "summary", "content": summary}] + recent_range

    def check_nudge(self, current_context_size: int, max_window: int) -> Optional[str]:
        """Check if context nudge needed."""
        usage_pct = current_context_size / max_window

        if usage_pct >= self.max_context_pct:
            return "strong"  # Aggressive pruning needed
        elif usage_pct >= self.max_context_pct * 0.9:
            return "soft"  # Gentle housekeeping
        elif usage_pct < self.min_context_pct:
            return None  # No action

        return None

    def get_pruning_stats(self) -> dict:
        """Return pruning statistics."""
        return {
            "compressions_performed": self.compressions,
            "duplicates_removed": self.deduplicates,
            "total_tokens_saved": self.tokens_saved,
            "max_context_threshold_pct": self.max_context_pct * 100,
            "min_context_threshold_pct": self.min_context_pct * 100,
        }

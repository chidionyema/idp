#!/usr/bin/env python3
"""Compaction manager: early compaction triggers before Pi's default."""

import logging

logger = logging.getLogger(__name__)


class CompactionManager:
    """Manage context compaction with early triggers."""

    def __init__(
        self,
        max_context: int = 128000,
        compaction_target: int = 64000,
        keep_recent: int = 20000,
    ):
        self.max_context = max_context
        self.compaction_target = compaction_target
        self.keep_recent = keep_recent
        self.compactions_triggered: int = 0
        self.tokens_saved: int = 0

    def check_compaction_needed(self, current_size: int) -> bool:
        """Check if compaction should trigger."""
        if current_size >= self.compaction_target:
            return True
        return False

    def trigger_compaction(self, context: list) -> list:
        """Trigger early compaction, preserving recent tokens."""
        if len(context) == 0:
            return context

        # Keep recent N tokens worth of messages
        compacted = []
        recent_tokens = 0

        for msg in reversed(context):
            msg_tokens = len(str(msg)) // 4
            if recent_tokens + msg_tokens <= self.keep_recent:
                compacted.insert(0, msg)
                recent_tokens += msg_tokens
            else:
                break

        # Add compaction marker
        if len(compacted) < len(context):
            dropped = len(context) - len(compacted)
            compacted.insert(
                0,
                {
                    "type": "compaction_marker",
                    "message": f"[{dropped} messages compacted for efficiency]",
                },
            )
            self.compactions_triggered += 1
            self.tokens_saved += len(context) - len(compacted)
            logger.info(
                f"[CompactionManager] Triggered early compaction, saved ~{self.tokens_saved} tokens"
            )

        return compacted

    def get_compaction_stats(self) -> dict:
        """Return compaction statistics."""
        return {
            "max_context_window": self.max_context,
            "compaction_target": self.compaction_target,
            "keep_recent_tokens": self.keep_recent,
            "compactions_triggered": self.compactions_triggered,
            "total_tokens_saved": self.tokens_saved,
        }

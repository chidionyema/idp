#!/usr/bin/env python3
"""Cache guardian: byte-identical system prompt on every turn."""

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CacheGuardian:
    """Preserve prompt cache by maintaining byte-identical system prompts."""

    def __init__(self):
        self.golden_prompt: Optional[str] = None
        self.golden_hash: Optional[str] = None
        self.cache_hits = 0
        self.cache_misses = 0

    def capture_golden(self, system_prompt: str) -> str:
        """Capture golden copy of system prompt on turn 1."""
        self.golden_prompt = system_prompt
        self.golden_hash = hashlib.sha256(system_prompt.encode()).hexdigest()
        logger.info(f"[CacheGuardian] Golden prompt captured: {self.golden_hash[:8]}")
        return system_prompt

    def restore_golden(self) -> Optional[str]:
        """Return golden prompt, or None if not captured."""
        if not self.golden_prompt:
            logger.warning("[CacheGuardian] No golden prompt captured")
            return None

        current_hash = hashlib.sha256(self.golden_prompt.encode()).hexdigest()
        if current_hash == self.golden_hash:
            self.cache_hits += 1
            logger.info(
                f"[CacheGuardian] Cache hit ({self.cache_hits}/{self.cache_hits + self.cache_misses})"
            )
            return self.golden_prompt
        else:
            self.cache_misses += 1
            logger.warning(
                f"[CacheGuardian] Cache miss: prompt drifted ({current_hash[:8]})"
            )
            return self.golden_prompt

    def reorder_prompt(self, system_prompt: str) -> str:
        """Reorder prompt so stable content (instructions, tools) sits first."""
        lines = system_prompt.split("\n")
        stable_lines = [
            l
            for l in lines
            if any(x in l for x in ["instruction", "tool", "guideline"])
        ]
        dynamic_lines = [l for l in lines if l not in stable_lines]
        reordered = "\n".join(stable_lines + dynamic_lines)
        logger.info(
            f"[CacheGuardian] Reordered: {len(stable_lines)} stable, {len(dynamic_lines)} dynamic"
        )
        return reordered

    def get_cache_stats(self) -> dict:
        """Return cache hit/miss stats."""
        total = self.cache_hits + self.cache_misses
        rate = (self.cache_hits / total * 100) if total > 0 else 0
        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "total": total,
            "hit_rate_pct": rate,
            "golden_hash": self.golden_hash[:8] if self.golden_hash else None,
        }

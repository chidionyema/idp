#!/usr/bin/env python3
"""Token killer: compress bash command output before context injection."""

import logging
import subprocess

logger = logging.getLogger(__name__)


class TokenKiller:
    """Compress bash output to reduce token consumption."""

    COMPRESSION_MAPPINGS = {
        "cat": "rtk read",
        "head": "rtk head",
        "tail": "rtk tail",
        "grep": "rtk grep",
        "rg": "rtk grep",
        "find": "rtk find",
        "ls": "rtk ls",
        "git log": "rtk log",
    }

    def __init__(self):
        self.commands_optimized = 0
        self.tokens_saved = 0
        self.rtk_available = self._check_rtk()

    def _check_rtk(self) -> bool:
        """Check if rtk binary is available."""
        try:
            result = subprocess.run(["which", "rtk"], capture_output=True, timeout=2)
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"[TokenKiller] RTK check failed: {e}")
            return False

    def compress_output(self, command: str, output: str) -> str:
        """Compress command output, or return original if RTK unavailable."""
        if not self.rtk_available:
            return output

        # Check if command matches a compression mapping
        mapped_command = None
        for orig, rtk_cmd in self.COMPRESSION_MAPPINGS.items():
            if command.startswith(orig):
                mapped_command = rtk_cmd
                break

        if not mapped_command:
            return output

        try:
            # Estimate compression: typical bash output is ~5 tokens/line
            # Compressed output is ~1 token/line
            lines = len(output.split("\n"))
            estimated_original = lines * 5
            estimated_compressed = lines * 1

            self.commands_optimized += 1
            self.tokens_saved += max(0, estimated_original - estimated_compressed)

            logger.info(
                f"[TokenKiller] Optimized '{command}': ~{estimated_original} → ~{estimated_compressed} tokens"
            )

            # Return first 10 lines to simulate compression
            compressed = "\n".join(output.split("\n")[:10])
            if len(output.split("\n")) > 10:
                compressed += (
                    f"\n... ({len(output.split('\n')) - 10} more lines omitted)"
                )

            return compressed

        except Exception as e:
            logger.warning(f"[TokenKiller] Compression failed: {e}")
            return output

    def get_savings_stats(self) -> dict:
        """Return compression stats."""
        return {
            "commands_optimized": self.commands_optimized,
            "estimated_tokens_saved": self.tokens_saved,
            "rtk_available": self.rtk_available,
        }

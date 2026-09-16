#!/usr/bin/env python3
"""Budget orchestrator: enforce per-agent token budgets with model routing."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ModelTier(str, Enum):
    """Available model tiers."""

    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


@dataclass
class RoutingRule:
    """Route agent to model based on task type."""

    task_type: str  # "draft", "review", "qa"
    target_model: ModelTier
    token_budget: int


class TokenBudgetOrchestrator:
    """Enforce per-agent token budgets with model routing."""

    DEFAULT_ROUTING = [
        RoutingRule("draft", ModelTier.HAIKU, 10000),
        RoutingRule("review", ModelTier.SONNET, 30000),
        RoutingRule("qa", ModelTier.OPUS, 50000),
    ]

    def __init__(self):
        self.routing_rules = self.DEFAULT_ROUTING
        self.agent_budgets = {}  # agent_id -> remaining tokens
        self.agent_models = {}  # agent_id -> model tier used
        self.total_spend = 0

    def register_agent(self, agent_id: str, initial_budget: int) -> None:
        """Register agent with token budget."""
        self.agent_budgets[agent_id] = initial_budget
        logger.info(
            f"[BudgetOrchestrator] Registered agent '{agent_id}' with {initial_budget} tokens"
        )

    def route_call(self, agent_id: str, task_type: str) -> Optional[ModelTier]:
        """Route agent to model, or None if budget exceeded."""
        rule = next((r for r in self.routing_rules if r.task_type == task_type), None)
        if not rule:
            logger.warning(
                f"[BudgetOrchestrator] No routing rule for task '{task_type}'"
            )
            return None

        remaining = self.agent_budgets.get(agent_id, 0)
        if remaining <= 0:
            logger.error(
                f"[BudgetOrchestrator] Agent '{agent_id}' budget exceeded, blocking call"
            )
            return None

        self.agent_models[agent_id] = rule.target_model
        logger.info(
            f"[BudgetOrchestrator] Route agent '{agent_id}' to {rule.target_model} for '{task_type}' (remaining: {remaining})"
        )
        return rule.target_model

    def consume_tokens(self, agent_id: str, tokens: int) -> None:
        """Deduct tokens from agent budget."""
        if agent_id in self.agent_budgets:
            self.agent_budgets[agent_id] -= tokens
            self.total_spend += tokens
            logger.info(
                f"[BudgetOrchestrator] Agent '{agent_id}' consumed {tokens} tokens (remaining: {self.agent_budgets[agent_id]})"
            )

    def get_budget_stats(self) -> dict:
        """Return budget stats."""
        return {
            "total_spend": self.total_spend,
            "agents": {
                agent_id: {
                    "remaining": budget,
                    "model": self.agent_models.get(agent_id, "unknown"),
                }
                for agent_id, budget in self.agent_budgets.items()
            },
        }

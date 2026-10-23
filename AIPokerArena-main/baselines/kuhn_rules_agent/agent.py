"""Submission-shaped wrapper around the readable Kuhn rules baseline."""

from arena.baselines import SimpleKuhnRulesAgent


def create_agent() -> SimpleKuhnRulesAgent:
    return SimpleKuhnRulesAgent()

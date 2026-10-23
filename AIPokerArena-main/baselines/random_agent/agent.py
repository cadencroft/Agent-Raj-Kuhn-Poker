"""Submission-shaped wrapper around the packaged random baseline."""

from arena.baselines import RandomAgent


def create_agent() -> RandomAgent:
    return RandomAgent()

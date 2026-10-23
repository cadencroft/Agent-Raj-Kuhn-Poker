"""Conceptual human agent adapter for synchronous frontends."""

from __future__ import annotations

from typing import Protocol

from arena.api.actions import Action
from arena.api.agent import PokerAgent
from arena.api.observation import Observation


class HumanActionProvider(Protocol):
    def wait_for_action(
        self,
        observation: Observation,
        legal_actions: tuple[Action, ...],
    ) -> Action: ...


class HumanAgent(PokerAgent):
    """Adapt human input to the public agent contract.

    The browser controller uses a pausable referee instead of blocking its HTTP
    event loop, but other synchronous frontends can use this adapter directly.
    """

    def __init__(self, action_provider: HumanActionProvider) -> None:
        self.action_provider = action_provider

    def act(
        self,
        observation: Observation,
        legal_actions: tuple[Action, ...],
    ) -> Action:
        return self.action_provider.wait_for_action(observation, legal_actions)

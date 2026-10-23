"""Understandable baseline agents for teaching and smoke tests."""

from __future__ import annotations

import hashlib
import random

from arena.api.actions import Action, Call, Check, Fold, RaiseTo
from arena.api.observation import Observation
from arena.api.results import MatchContext


class RandomAgent:
    """Choose uniformly from the concrete legal actions."""

    def __init__(self) -> None:
        self._rng = random.Random(0)

    def new_match(self, context: MatchContext) -> None:
        material = f"{context.seed}:{context.player_id}:random".encode()
        derived_seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
        self._rng.seed(derived_seed)

    def act(
        self,
        observation: Observation,
        legal_actions: tuple[Action, ...],
    ) -> Action:
        del observation
        return self._rng.choice(legal_actions)


class SimpleKuhnRulesAgent:
    """A deliberately readable, non-optimal first-assignment opponent."""

    def act(
        self,
        observation: Observation,
        legal_actions: tuple[Action, ...],
    ) -> Action:
        card = observation.toy_private_card

        if card == "K":
            return _first_available(legal_actions, RaiseTo, Call, Check)
        if card == "J":
            return _first_available(legal_actions, Check, Fold)
        return _first_available(legal_actions, Check, Call, Fold)


class AlwaysFoldAgent:
    """Check when possible, otherwise fold."""

    def act(
        self,
        observation: Observation,
        legal_actions: tuple[Action, ...],
    ) -> Action:
        del observation
        return _first_available(legal_actions, Check, Fold, Call)


def _first_available(
    legal_actions: tuple[Action, ...],
    *preferences: type[Action],
) -> Action:
    for preferred_type in preferences:
        for action in legal_actions:
            if isinstance(action, preferred_type):
                return action
    return legal_actions[0]

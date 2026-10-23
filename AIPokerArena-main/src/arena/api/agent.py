"""The student agent protocol."""

from abc import ABC, abstractmethod

from arena.api.actions import Action
from arena.api.observation import Observation
from arena.api.results import HandResult, MatchContext, MatchResult


class PokerAgent(ABC):
    """Optional base class for poker agents.

    Subclassing is not required; any object with a compatible ``act`` method works.
    """

    def new_match(self, context: MatchContext) -> None:
        """Receive public match configuration before the first hand."""
        return None

    def new_hand(self, observation: Observation) -> None:
        """Receive this player's initial observation for a new hand."""
        return None

    @abstractmethod
    def act(
        self,
        observation: Observation,
        legal_actions: tuple[Action, ...],
    ) -> Action:
        """Choose and return one of ``legal_actions``."""
        raise NotImplementedError

    def hand_finished(self, result: HandResult) -> None:
        """Receive the public result after a hand."""
        return None

    def match_finished(self, result: MatchResult) -> None:
        """Receive the aggregate result after a match."""
        return None

"""Public lifecycle and result objects."""

from dataclasses import dataclass

from arena.api.observation import ObservedAction


@dataclass(frozen=True, slots=True)
class MatchContext:
    game: str
    match_id: str
    player_id: str
    hands: int
    seed: int


@dataclass(frozen=True, slots=True)
class HandResult:
    game: str
    hand_id: str
    seed: int
    players: tuple[str, ...]
    payouts: tuple[int, ...]
    winner_ids: tuple[str, ...]
    showdown: bool
    revealed_cards: tuple[str | None, ...]
    action_history: tuple[ObservedAction, ...]

    def payout_for(self, player_id: str) -> int:
        """Return net chips won by ``player_id`` in this hand."""
        return self.payouts[self.players.index(player_id)]


@dataclass(frozen=True, slots=True)
class MatchResult:
    game: str
    match_id: str
    seed: int
    hands: int
    players: tuple[str, ...]
    total_payouts: tuple[int, ...]
    timeouts: tuple[int, ...]
    invalid_actions: tuple[int, ...]
    crashes: tuple[int, ...]

    def payout_for(self, player_id: str) -> int:
        """Return aggregate net chips won by ``player_id``."""
        return self.total_payouts[self.players.index(player_id)]

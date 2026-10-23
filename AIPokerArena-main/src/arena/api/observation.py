"""Immutable, player-visible state passed across the agent boundary."""

from dataclasses import dataclass

from arena.api.actions import Action


@dataclass(frozen=True, slots=True)
class PublicPlayerState:
    seat: int
    player_id: str
    stack: int
    committed: int
    folded: bool
    all_in: bool


@dataclass(frozen=True, slots=True)
class ObservedAction:
    seat: int
    player_id: str
    action: Action


@dataclass(frozen=True, slots=True)
class Observation:
    """A fresh snapshot containing only information visible to one player."""

    game: str
    hand_id: str
    player_id: str
    seat: int
    private_cards: tuple[str, ...]
    board_cards: tuple[str, ...]
    pot: int
    current_bet: int
    amount_to_call: int
    dealer_seat: int
    small_blind: int
    big_blind: int
    players: tuple[PublicPlayerState, ...]
    action_history: tuple[ObservedAction, ...]
    street: str
    toy_private_card: str | None = None

"""Explicit, sanitized values rendered by the browser GUI."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PlayerView:
    seat: int
    player_id: str
    stack: int
    committed: int
    folded: bool
    is_human: bool


@dataclass(frozen=True, slots=True)
class ActionView:
    action_id: str
    label: str


@dataclass(frozen=True, slots=True)
class HistoryView:
    player_id: str
    label: str


@dataclass(frozen=True, slots=True)
class TableView:
    game: str
    hand_id: str
    hand_number: int
    hero_seat: int
    private_cards: tuple[str, ...]
    opponent_revealed_cards: tuple[str, ...]
    board_cards: tuple[str, ...]
    pot: int
    amount_to_call: int
    dealer_seat: int
    players: tuple[PlayerView, ...]
    actions: tuple[HistoryView, ...]
    legal_actions: tuple[ActionView, ...]
    hand_complete: bool
    result_message: str | None
    bot_faults: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

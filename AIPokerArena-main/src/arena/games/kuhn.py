"""A compact, authoritative two-player Kuhn poker implementation."""

from __future__ import annotations

import random
from collections.abc import Sequence

from arena.api.actions import Action, Call, Check, Fold, RaiseTo, action_name
from arena.api.observation import Observation, ObservedAction, PublicPlayerState
from arena.api.results import HandResult
from arena.games.base import HandFinishedError, IllegalActionError, OutOfTurnError

KUHN_CARDS = ("J", "Q", "K")
_CARD_RANK = {card: rank for rank, card in enumerate(KUHN_CARDS)}


class KuhnHand:
    """Authoritative state for one hand of Kuhn poker.

    Each player antes one chip and has one chip behind. A bet is one chip. The
    object is deliberately never passed to agent code; callers use :meth:`observe`.
    """

    game = "kuhn"

    def __init__(
        self,
        players: Sequence[str],
        *,
        seed: int,
        hand_id: str,
    ) -> None:
        if len(players) != 2:
            raise ValueError("Kuhn poker requires exactly two players")
        if players[0] == players[1]:
            raise ValueError("Player IDs must be unique")

        self.hand_id = hand_id
        self.seed = seed
        self.players = (players[0], players[1])
        self._rng = random.Random(seed)
        deck = list(KUHN_CARDS)
        self._rng.shuffle(deck)
        self._cards = (deck[0], deck[1])
        self._undealt_card = deck[2]
        self._committed = [1, 1]
        self._folded = [False, False]
        self._history: list[ObservedAction] = []
        self._finished = False

    @property
    def finished(self) -> bool:
        return self._finished

    @property
    def current_player(self) -> int:
        """Return the acting seat, derived only from public betting history."""
        if self._finished:
            raise HandFinishedError("The hand is already finished")
        names = tuple(action_name(item.action) for item in self._history)
        if names == ():
            return 0
        if names in (("check",), ("raise_to",)):
            return 1
        if names == ("check", "raise_to"):
            return 0
        raise RuntimeError(f"Invalid non-terminal Kuhn history: {names!r}")

    def legal_actions(self, seat: int) -> tuple[Action, ...]:
        """Return concrete legal actions for the current player."""
        if seat != self.current_player:
            raise OutOfTurnError(f"Seat {seat} is not the current player")
        names = tuple(action_name(item.action) for item in self._history)
        if names in ((), ("check",)):
            return (Check(), RaiseTo(2))
        if names in (("raise_to",), ("check", "raise_to")):
            return (Fold(), Call())
        raise RuntimeError(f"Invalid Kuhn history: {names!r}")

    def observe(self, seat: int) -> Observation:
        """Create a fresh player-visible snapshot with no hidden references."""
        if seat not in (0, 1):
            raise ValueError(f"Invalid seat: {seat}")
        current_bet = max(self._committed)
        public_players = tuple(
            PublicPlayerState(
                seat=player_seat,
                player_id=player_id,
                stack=2 - self._committed[player_seat],
                committed=self._committed[player_seat],
                folded=self._folded[player_seat],
                all_in=self._committed[player_seat] == 2,
            )
            for player_seat, player_id in enumerate(self.players)
        )
        history = tuple(
            ObservedAction(
                seat=item.seat,
                player_id=item.player_id,
                action=item.action,
            )
            for item in self._history
        )
        card = self._cards[seat]
        return Observation(
            game=self.game,
            hand_id=self.hand_id,
            player_id=self.players[seat],
            seat=seat,
            private_cards=(card,),
            board_cards=(),
            pot=sum(self._committed),
            current_bet=current_bet,
            amount_to_call=current_bet - self._committed[seat],
            dealer_seat=0,
            small_blind=0,
            big_blind=0,
            players=public_players,
            action_history=history,
            street="single_round",
            toy_private_card=card,
        )

    def apply_action(self, seat: int, action: Action) -> None:
        """Validate and apply one action to authoritative state."""
        if self._finished:
            raise HandFinishedError("The hand is already finished")
        if seat != self.current_player:
            raise OutOfTurnError(f"Seat {seat} is not the current player")
        legal = self.legal_actions(seat)
        if action not in legal:
            raise IllegalActionError(
                f"{action!r} is illegal; expected one of {legal!r}"
            )

        if isinstance(action, RaiseTo):
            self._committed[seat] = action.amount
        elif isinstance(action, Call):
            self._committed[seat] = max(self._committed)
        elif isinstance(action, Fold):
            self._folded[seat] = True

        self._history.append(
            ObservedAction(
                seat=seat,
                player_id=self.players[seat],
                action=action,
            )
        )
        self._finished = self._is_terminal()

    def result(self) -> HandResult:
        """Settle a completed hand and return immutable public results."""
        if not self._finished:
            raise HandFinishedError("Cannot settle an unfinished hand")

        showdown = not any(self._folded)
        if showdown:
            winner = max(range(2), key=lambda seat: _CARD_RANK[self._cards[seat]])
        else:
            winner = 0 if self._folded[1] else 1

        pot = sum(self._committed)
        payouts = [-amount for amount in self._committed]
        payouts[winner] += pot
        revealed: tuple[str | None, ...] = self._cards if showdown else (None, None)

        return HandResult(
            game=self.game,
            hand_id=self.hand_id,
            seed=self.seed,
            players=self.players,
            payouts=(payouts[0], payouts[1]),
            winner_ids=(self.players[winner],),
            showdown=showdown,
            revealed_cards=revealed,
            action_history=tuple(self._history),
        )

    def audit_cards(self) -> tuple[str, str, str]:
        """Return dealt and undealt cards for instructor replay generation only."""
        if not self._finished:
            raise HandFinishedError("Audit data is available only after the hand")
        return (self._cards[0], self._cards[1], self._undealt_card)

    def _is_terminal(self) -> bool:
        names = tuple(action_name(item.action) for item in self._history)
        return names in {
            ("check", "check"),
            ("raise_to", "fold"),
            ("raise_to", "call"),
            ("check", "raise_to", "fold"),
            ("check", "raise_to", "call"),
        }

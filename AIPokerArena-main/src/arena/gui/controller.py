"""GUI state management, separate from Kuhn game logic."""

from __future__ import annotations

import logging
import random
import threading

from arena.api.actions import Action, Call, Check, Fold, RaiseTo, format_action
from arena.api.results import MatchContext
from arena.gui.view_models import ActionView, HistoryView, PlayerView, TableView
from arena.match.interactive import InteractiveKuhnReferee
from arena.match.referee import AgentLike

LOGGER = logging.getLogger(__name__)


class KuhnGuiController:
    """Coordinate browser input with a pausable authoritative referee."""

    def __init__(
        self,
        bot: AgentLike,
        *,
        bot_id: str = "Bot",
        seed: int = 42,
        action_timeout_seconds: float = 0.1,
    ) -> None:
        self.human_id = "Human"
        self.bot_id = bot_id
        self.bot = bot
        self.seed = seed
        self.action_timeout_seconds = action_timeout_seconds
        self._rng = random.Random(seed)
        self._hand_number = 0
        self._lock = threading.RLock()
        self._session: InteractiveKuhnReferee
        self._notify_new_match()
        self.next_hand()

    def view(self) -> TableView:
        with self._lock:
            observation = self._session.observe_human()
            result = self._session.result()
            opponent_cards: tuple[str, ...] = ()
            result_message = None
            if result is not None:
                opponent_seat = 1 - self._session.human_seat
                revealed = result.revealed_cards[opponent_seat]
                if revealed is not None:
                    opponent_cards = (revealed,)
                payout = result.payout_for(self.human_id)
                if payout > 0:
                    result_message = f"You won {payout} chip(s)."
                elif payout < 0:
                    result_message = f"You lost {-payout} chip(s)."
                else:
                    result_message = "The hand was a tie."

            legal = tuple(
                ActionView(_action_id(action), _action_label(action))
                for action in self._session.legal_human_actions()
            )
            players = tuple(
                PlayerView(
                    seat=player.seat,
                    player_id=player.player_id,
                    stack=player.stack,
                    committed=player.committed,
                    folded=player.folded,
                    is_human=player.player_id == self.human_id,
                )
                for player in observation.players
            )
            history = tuple(
                HistoryView(item.player_id, format_action(item.action))
                for item in observation.action_history
            )
            faults = self._session.bot_faults
            return TableView(
                game="Kuhn poker",
                hand_id=observation.hand_id,
                hand_number=self._hand_number,
                hero_seat=self._session.human_seat,
                private_cards=observation.private_cards,
                opponent_revealed_cards=opponent_cards,
                board_cards=(),
                pot=observation.pot,
                amount_to_call=observation.amount_to_call,
                dealer_seat=observation.dealer_seat,
                players=players,
                actions=history,
                legal_actions=legal,
                hand_complete=self._session.finished,
                result_message=result_message,
                bot_faults=faults.timeouts + faults.invalid_actions + faults.crashes,
            )

    def submit_action(self, action_id: str) -> TableView:
        with self._lock:
            choices = {
                _action_id(action): action
                for action in self._session.legal_human_actions()
            }
            action = choices.get(action_id)
            if action is None:
                raise ValueError(f"Action is not currently legal: {action_id!r}")
            self._session.submit_human_action(action)
            return self.view()

    def next_hand(self) -> TableView:
        with self._lock:
            if hasattr(self, "_session") and not self._session.finished:
                raise ValueError("Finish the current hand before starting another")
            self._hand_number += 1
            hand_seed = self._rng.getrandbits(63)
            self._session = InteractiveKuhnReferee(
                human_id=self.human_id,
                bot_id=self.bot_id,
                bot=self.bot,
                human_seat=0,
                seed=hand_seed,
                hand_id=f"gui-{self.seed}-h{self._hand_number:06d}",
                action_timeout_seconds=self.action_timeout_seconds,
            )
            return self.view()

    def _notify_new_match(self) -> None:
        callback = getattr(self.bot, "new_match", None)
        if not callable(callback):
            return
        try:
            callback(
                MatchContext(
                    game="kuhn",
                    match_id=f"gui-{self.seed}",
                    player_id=self.bot_id,
                    hands=0,
                    seed=self.seed,
                )
            )
        except BaseException:
            LOGGER.exception("Bot new_match callback crashed")


def _action_id(action: Action) -> str:
    if isinstance(action, RaiseTo):
        return f"raise_to:{action.amount}"
    if isinstance(action, Check):
        return "check"
    if isinstance(action, Call):
        return "call"
    if isinstance(action, Fold):
        return "fold"
    raise TypeError(f"Unsupported action: {type(action).__name__}")


def _action_label(action: Action) -> str:
    if isinstance(action, RaiseTo):
        return "Bet 1"
    return format_action(action).title()

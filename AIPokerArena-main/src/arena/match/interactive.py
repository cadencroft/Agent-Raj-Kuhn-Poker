"""A pausable referee session used by the human-vs-agent GUI."""

from __future__ import annotations

import logging

from arena.api.actions import Action, Call, Check, Fold
from arena.api.observation import Observation
from arena.api.results import HandResult
from arena.games.base import OutOfTurnError
from arena.games.kuhn import KuhnHand
from arena.match.referee import AgentFaults, AgentLike
from arena.match.timeout import ActionTimeoutError, call_with_timeout

LOGGER = logging.getLogger(__name__)


class InteractiveKuhnReferee:
    """Own one authoritative hand and pause whenever the human must act."""

    def __init__(
        self,
        *,
        human_id: str,
        bot_id: str,
        bot: AgentLike,
        human_seat: int,
        seed: int,
        hand_id: str,
        action_timeout_seconds: float = 0.1,
    ) -> None:
        if human_seat not in (0, 1):
            raise ValueError("human_seat must be 0 or 1")
        self.human_id = human_id
        self.bot_id = bot_id
        self.bot = bot
        self.human_seat = human_seat
        self.bot_seat = 1 - human_seat
        players = ["", ""]
        players[self.human_seat] = human_id
        players[self.bot_seat] = bot_id
        self._hand = KuhnHand(tuple(players), seed=seed, hand_id=hand_id)
        self.action_timeout_seconds = action_timeout_seconds
        self.bot_faults = AgentFaults()
        self._notify_bot_new_hand()
        self.advance_to_human()

    @property
    def finished(self) -> bool:
        return self._hand.finished

    @property
    def hand_id(self) -> str:
        return self._hand.hand_id

    @property
    def seed(self) -> int:
        return self._hand.seed

    @property
    def current_player_id(self) -> str | None:
        if self.finished:
            return None
        return self._hand.players[self._hand.current_player]

    def observe_human(self) -> Observation:
        return self._hand.observe(self.human_seat)

    def legal_human_actions(self) -> tuple[Action, ...]:
        if self.finished or self._hand.current_player != self.human_seat:
            return ()
        return self._hand.legal_actions(self.human_seat)

    def submit_human_action(self, action: Action) -> None:
        """Validate a browser-supplied action and continue through bot turns."""
        if self.finished or self._hand.current_player != self.human_seat:
            raise OutOfTurnError("It is not the human player's turn")
        self._hand.apply_action(self.human_seat, action)
        self.advance_to_human()

    def advance_to_human(self) -> None:
        """Run bot decisions until human input is needed or the hand ends."""
        while not self.finished and self._hand.current_player == self.bot_seat:
            observation = self._hand.observe(self.bot_seat)
            legal_actions = self._hand.legal_actions(self.bot_seat)
            action = self._request_bot_action(observation, legal_actions)
            self._hand.apply_action(self.bot_seat, action)

    def result(self) -> HandResult | None:
        return self._hand.result() if self.finished else None

    def _request_bot_action(
        self,
        observation: Observation,
        legal_actions: tuple[Action, ...],
    ) -> Action:
        try:
            candidate = call_with_timeout(
                lambda: self.bot.act(observation, legal_actions),
                self.action_timeout_seconds,
            )
        except ActionTimeoutError:
            self.bot_faults.timeouts += 1
            return _safe_action(legal_actions)
        except BaseException:
            self.bot_faults.crashes += 1
            LOGGER.exception("Bot crashed during interactive hand")
            return _safe_action(legal_actions)
        if not isinstance(candidate, Action) or candidate not in legal_actions:
            self.bot_faults.invalid_actions += 1
            return _safe_action(legal_actions)
        return candidate

    def _notify_bot_new_hand(self) -> None:
        callback = getattr(self.bot, "new_hand", None)
        if not callable(callback):
            return
        try:
            callback(self._hand.observe(self.bot_seat))
        except BaseException:
            self.bot_faults.crashes += 1
            LOGGER.exception("Bot new_hand callback crashed")


def _safe_action(legal_actions: tuple[Action, ...]) -> Action:
    for action_type in (Check, Call, Fold):
        for action in legal_actions:
            if isinstance(action, action_type):
                return action
    return legal_actions[0]

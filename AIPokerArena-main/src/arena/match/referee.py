"""Referee boundary between untrusted agents and authoritative Kuhn state."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from arena.api.actions import Action, Call, Check, Fold, action_to_dict
from arena.api.observation import Observation
from arena.api.results import HandResult
from arena.games.kuhn import KuhnHand
from arena.match.timeout import ActionTimeoutError, call_with_timeout

LOGGER = logging.getLogger(__name__)


class AgentLike(Protocol):
    def act(
        self,
        observation: Observation,
        legal_actions: tuple[Action, ...],
    ) -> Action: ...


@dataclass(slots=True)
class AgentFaults:
    timeouts: int = 0
    invalid_actions: int = 0
    crashes: int = 0

    def add(self, other: AgentFaults) -> None:
        self.timeouts += other.timeouts
        self.invalid_actions += other.invalid_actions
        self.crashes += other.crashes


@dataclass(frozen=True, slots=True)
class HandRun:
    result: HandResult
    faults: dict[str, AgentFaults]
    replay: dict[str, Any]


class KuhnReferee:
    """Run one Kuhn hand while treating every agent response as untrusted."""

    def __init__(self, *, action_timeout_seconds: float = 0.1) -> None:
        if action_timeout_seconds <= 0:
            raise ValueError("action_timeout_seconds must be positive")
        self.action_timeout_seconds = action_timeout_seconds

    def play_hand(
        self,
        agents: dict[str, AgentLike],
        players: tuple[str, str],
        *,
        seed: int,
        hand_id: str,
    ) -> HandRun:
        if set(agents) != set(players):
            raise ValueError("agents must contain exactly the two seated players")

        hand = KuhnHand(players, seed=seed, hand_id=hand_id)
        faults = {player_id: AgentFaults() for player_id in players}
        events: list[dict[str, Any]] = [
            {"type": "hand_started", "pot": 2},
            {"type": "cards_dealt", "count_per_player": 1},
        ]

        self._notify_new_hand(agents, hand, players, faults, events)
        while not hand.finished:
            seat = hand.current_player
            player_id = players[seat]
            observation = hand.observe(seat)
            legal_actions = hand.legal_actions(seat)
            events.append(
                {
                    "type": "action_requested",
                    "seat": seat,
                    "player_id": player_id,
                    "legal_actions": [
                        action_to_dict(action) for action in legal_actions
                    ],
                }
            )
            action, fault_type = self._request_action(
                agents[player_id],
                observation,
                legal_actions,
                faults[player_id],
            )
            action_event: dict[str, Any] = {
                "type": "action",
                "seat": seat,
                "player_id": player_id,
                "action": action_to_dict(action),
            }
            if fault_type is not None:
                action_event["substituted_for"] = fault_type
            events.append(action_event)
            hand.apply_action(seat, action)

        result = hand.result()
        dealt_0, dealt_1, undealt = hand.audit_cards()
        events.append(
            {
                "type": "hand_finished",
                "payouts": list(result.payouts),
                "winners": list(result.winner_ids),
                "showdown": result.showdown,
            }
        )
        replay: dict[str, Any] = {
            "schema_version": 1,
            "game": "kuhn",
            "hand_id": hand_id,
            "seed": seed,
            "players": list(players),
            "button_seat": 0,
            "starting_stacks": [2, 2],
            "private_cards": [dealt_0, dealt_1],
            "undealt_card": undealt,
            "events": events,
            "payouts": list(result.payouts),
        }
        return HandRun(result=result, faults=faults, replay=replay)

    def _request_action(
        self,
        agent: AgentLike,
        observation: Observation,
        legal_actions: tuple[Action, ...],
        faults: AgentFaults,
    ) -> tuple[Action, str | None]:
        try:
            candidate = call_with_timeout(
                lambda: agent.act(observation, legal_actions),
                self.action_timeout_seconds,
            )
        except ActionTimeoutError:
            faults.timeouts += 1
            LOGGER.warning("Agent timed out in hand %s", observation.hand_id)
            return _safe_action(legal_actions), "timeout"
        except BaseException:  # agents are untrusted; keep the match alive
            faults.crashes += 1
            LOGGER.exception("Agent crashed in hand %s", observation.hand_id)
            return _safe_action(legal_actions), "crash"

        if not isinstance(candidate, Action) or candidate not in legal_actions:
            faults.invalid_actions += 1
            LOGGER.warning(
                "Agent returned an invalid %s in hand %s",
                type(candidate).__name__,
                observation.hand_id,
            )
            return _safe_action(legal_actions), "invalid_action"
        return candidate, None

    def _notify_new_hand(
        self,
        agents: dict[str, AgentLike],
        hand: KuhnHand,
        players: tuple[str, str],
        faults: dict[str, AgentFaults],
        events: list[dict[str, Any]],
    ) -> None:
        for seat, player_id in enumerate(players):
            callback = getattr(agents[player_id], "new_hand", None)
            if callback is None:
                continue
            try:
                callback(hand.observe(seat))
            except BaseException:
                faults[player_id].crashes += 1
                events.append(
                    {
                        "type": "agent_callback_crash",
                        "callback": "new_hand",
                        "player_id": player_id,
                    }
                )
                LOGGER.exception("Agent new_hand callback crashed")


def _safe_action(legal_actions: tuple[Action, ...]) -> Action:
    """Choose a deterministic, conservative fallback: check, call, then fold."""
    for action_type in (Check, Call, Fold):
        for action in legal_actions:
            if isinstance(action, action_type):
                return action
    return legal_actions[0]

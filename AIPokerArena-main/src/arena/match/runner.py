"""Deterministic, seat-balanced match runner."""

from __future__ import annotations

import logging
import random
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from arena.api.results import MatchContext, MatchResult
from arena.match.referee import AgentFaults, AgentLike, KuhnReferee
from arena.match.replay import ReplayWriter

LOGGER = logging.getLogger(__name__)


def run_kuhn_match(
    agents: Mapping[str, object],
    *,
    hands: int = 1000,
    seed: int = 42,
    action_timeout_seconds: float = 0.1,
    replay_path: str | Path | None = None,
    match_id: str | None = None,
) -> MatchResult:
    """Run a reproducible match, reversing seats every hand."""
    if len(agents) != 2:
        raise ValueError("A Kuhn match requires exactly two agents")
    if hands <= 0:
        raise ValueError("hands must be positive")
    player_ids = tuple(agents)
    if len(set(player_ids)) != 2:
        raise ValueError("Player IDs must be unique")
    for player_id, agent in agents.items():
        if not callable(getattr(agent, "act", None)):
            raise TypeError(f"Agent {player_id!r} has no callable act method")

    resolved_match_id = match_id or f"kuhn-{seed}"
    totals = {player_id: 0 for player_id in player_ids}
    faults = {player_id: AgentFaults() for player_id in player_ids}
    rng = random.Random(seed)
    referee = KuhnReferee(action_timeout_seconds=action_timeout_seconds)
    typed_agents = cast(dict[str, AgentLike], dict(agents))

    for player_id, agent in agents.items():
        context = MatchContext(
            game="kuhn",
            match_id=resolved_match_id,
            player_id=player_id,
            hands=hands,
            seed=seed,
        )
        _call_lifecycle(agent, "new_match", context, faults[player_id])

    writer = ReplayWriter(replay_path) if replay_path is not None else None
    try:
        for hand_number in range(1, hands + 1):
            seated = (player_ids[0], player_ids[1])
            if hand_number % 2 == 0:
                seated = (seated[1], seated[0])
            hand_seed = rng.getrandbits(63)
            hand_id = f"{resolved_match_id}-h{hand_number:06d}"
            hand_run = referee.play_hand(
                typed_agents,
                seated,
                seed=hand_seed,
                hand_id=hand_id,
            )
            for seat, player_id in enumerate(hand_run.result.players):
                totals[player_id] += hand_run.result.payouts[seat]
                faults[player_id].add(hand_run.faults[player_id])
                _call_lifecycle(
                    agents[player_id],
                    "hand_finished",
                    hand_run.result,
                    faults[player_id],
                )
            if writer is not None:
                writer.write(hand_run.replay)
    finally:
        if writer is not None:
            writer.close()

    result = MatchResult(
        game="kuhn",
        match_id=resolved_match_id,
        seed=seed,
        hands=hands,
        players=(player_ids[0], player_ids[1]),
        total_payouts=tuple(totals[player_id] for player_id in player_ids),
        timeouts=tuple(faults[player_id].timeouts for player_id in player_ids),
        invalid_actions=tuple(
            faults[player_id].invalid_actions for player_id in player_ids
        ),
        crashes=tuple(faults[player_id].crashes for player_id in player_ids),
    )
    for player_id, agent in agents.items():
        _call_lifecycle(agent, "match_finished", result, faults[player_id])
    return result


def _call_lifecycle(
    agent: object,
    callback_name: str,
    value: object,
    faults: AgentFaults,
) -> None:
    callback = getattr(agent, callback_name, None)
    if callback is None:
        return
    try:
        callback(value)
    except BaseException:
        faults.crashes += 1
        LOGGER.exception("Agent %s callback crashed", callback_name)

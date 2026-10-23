"""Simple deterministic round-robin scheduling for the Kuhn MVP."""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from arena.api.results import MatchResult
from arena.match.runner import run_kuhn_match


@dataclass(frozen=True, slots=True)
class Standing:
    player_id: str
    hands: int
    total_chips: int
    chips_per_100: float
    timeouts: int
    invalid_actions: int
    crashes: int


@dataclass(frozen=True, slots=True)
class TournamentResult:
    seed: int
    hands_per_matchup: int
    standings: tuple[Standing, ...]
    matches: tuple[MatchResult, ...]


def run_round_robin(
    agent_factories: Mapping[str, Callable[[], object]],
    *,
    hands_per_matchup: int = 1000,
    seed: int = 42,
    action_timeout_seconds: float = 0.1,
) -> TournamentResult:
    """Play every pair once, with alternating seats inside each match."""
    if len(agent_factories) < 2:
        raise ValueError("A tournament requires at least two agents")
    if hands_per_matchup <= 0:
        raise ValueError("hands_per_matchup must be positive")

    names = tuple(agent_factories)
    totals = {
        name: {
            "hands": 0,
            "chips": 0,
            "timeouts": 0,
            "invalid": 0,
            "crashes": 0,
        }
        for name in names
    }
    matches: list[MatchResult] = []
    rng = random.Random(seed)

    for left_index, left_name in enumerate(names):
        for right_name in names[left_index + 1 :]:
            match_seed = rng.getrandbits(63)
            match = run_kuhn_match(
                {
                    left_name: agent_factories[left_name](),
                    right_name: agent_factories[right_name](),
                },
                hands=hands_per_matchup,
                seed=match_seed,
                action_timeout_seconds=action_timeout_seconds,
                match_id=f"round-robin-{left_index + 1}-{len(matches) + 1}",
            )
            matches.append(match)
            for index, name in enumerate(match.players):
                row = totals[name]
                row["hands"] += match.hands
                row["chips"] += match.total_payouts[index]
                row["timeouts"] += match.timeouts[index]
                row["invalid"] += match.invalid_actions[index]
                row["crashes"] += match.crashes[index]

    standings = tuple(
        sorted(
            (
                Standing(
                    player_id=name,
                    hands=row["hands"],
                    total_chips=row["chips"],
                    chips_per_100=100.0 * row["chips"] / row["hands"],
                    timeouts=row["timeouts"],
                    invalid_actions=row["invalid"],
                    crashes=row["crashes"],
                )
                for name, row in totals.items()
            ),
            key=lambda standing: (-standing.chips_per_100, standing.player_id),
        )
    )
    return TournamentResult(
        seed=seed,
        hands_per_matchup=hands_per_matchup,
        standings=standings,
        matches=tuple(matches),
    )

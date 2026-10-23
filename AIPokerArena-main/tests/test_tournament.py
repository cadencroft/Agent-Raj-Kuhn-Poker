from arena.baselines import AlwaysFoldAgent, RandomAgent, SimpleKuhnRulesAgent
from arena.tournament import run_round_robin


def test_round_robin_plays_each_pair_and_conserves_chips() -> None:
    result = run_round_robin(
        {
            "fold": AlwaysFoldAgent,
            "random": RandomAgent,
            "rules": SimpleKuhnRulesAgent,
        },
        hands_per_matchup=10,
        seed=11,
    )
    assert len(result.matches) == 3
    assert len(result.standings) == 3
    assert all(standing.hands == 20 for standing in result.standings)
    assert sum(standing.total_chips for standing in result.standings) == 0

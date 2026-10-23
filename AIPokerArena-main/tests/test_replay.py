import json

from arena.baselines import SimpleKuhnRulesAgent
from arena.match import load_replays, run_kuhn_match


def test_replay_is_complete_and_reproducible(tmp_path) -> None:
    left_path = tmp_path / "left.jsonl"
    right_path = tmp_path / "right.jsonl"

    for path in (left_path, right_path):
        run_kuhn_match(
            {"alice": SimpleKuhnRulesAgent(), "bob": SimpleKuhnRulesAgent()},
            hands=5,
            seed=44,
            replay_path=path,
        )

    assert left_path.read_text() == right_path.read_text()
    records = list(load_replays(left_path))
    assert len(records) == 5
    assert all(record["seed"] is not None for record in records)
    assert all(len(record["private_cards"]) == 2 for record in records)
    assert all(record["undealt_card"] in {"J", "Q", "K"} for record in records)
    assert all(sum(record["payouts"]) == 0 for record in records)
    assert json.loads(left_path.read_text().splitlines()[0])["schema_version"] == 1

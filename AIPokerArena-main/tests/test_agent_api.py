from dataclasses import FrozenInstanceError

import pytest

from arena import Check, Observation, RaiseTo
from arena.api import PublicPlayerState


def test_actions_are_value_objects() -> None:
    assert Check() == Check()
    assert RaiseTo(2) == RaiseTo(amount=2)
    assert RaiseTo(2) != RaiseTo(3)
    with pytest.raises(FrozenInstanceError):
        RaiseTo(2).amount = 3  # type: ignore[misc]


def test_observation_is_immutable() -> None:
    observation = Observation(
        game="kuhn",
        hand_id="h1",
        player_id="alice",
        seat=0,
        private_cards=("K",),
        board_cards=(),
        pot=2,
        current_bet=1,
        amount_to_call=0,
        dealer_seat=0,
        small_blind=0,
        big_blind=0,
        players=(PublicPlayerState(0, "alice", 1, 1, False, False),),
        action_history=(),
        street="single_round",
        toy_private_card="K",
    )
    with pytest.raises(FrozenInstanceError):
        observation.pot = 99  # type: ignore[misc]
    with pytest.raises(TypeError):
        vars(observation)

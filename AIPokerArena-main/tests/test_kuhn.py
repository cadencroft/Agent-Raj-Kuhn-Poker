import pytest

from arena import Action, Call, Check, Fold, RaiseTo
from arena.games.base import HandFinishedError, IllegalActionError, OutOfTurnError
from arena.games.kuhn import KuhnHand


def make_hand(seed: int = 1) -> KuhnHand:
    return KuhnHand(("alice", "bob"), seed=seed, hand_id="hand-1")


def test_bet_fold_settlement() -> None:
    hand = make_hand()
    hand.apply_action(0, RaiseTo(2))
    hand.apply_action(1, Fold())

    result = hand.result()
    assert result.payouts == (1, -1)
    assert result.winner_ids == ("alice",)
    assert not result.showdown
    assert result.revealed_cards == (None, None)


def test_check_bet_fold_settlement() -> None:
    hand = make_hand()
    hand.apply_action(0, Check())
    hand.apply_action(1, RaiseTo(2))
    hand.apply_action(0, Fold())
    assert hand.result().payouts == (-1, 1)


@pytest.mark.parametrize(
    "actions,absolute_payout",
    [
        ((Check(), Check()), 1),
        ((RaiseTo(2), Call()), 2),
        ((Check(), RaiseTo(2), Call()), 2),
    ],
)
def test_showdown_is_zero_sum(
    actions: tuple[Action, ...], absolute_payout: int
) -> None:
    hand = make_hand(seed=7)
    for action in actions:
        hand.apply_action(hand.current_player, action)
    result = hand.result()
    assert sorted(result.payouts) == [-absolute_payout, absolute_payout]
    assert sum(result.payouts) == 0
    assert result.showdown
    assert set(card for card in result.revealed_cards if card) <= {"J", "Q", "K"}


def test_legal_actions_follow_public_history() -> None:
    hand = make_hand()
    assert hand.current_player == 0
    assert hand.legal_actions(0) == (Check(), RaiseTo(2))
    hand.apply_action(0, Check())
    assert hand.current_player == 1
    assert hand.legal_actions(1) == (Check(), RaiseTo(2))
    hand.apply_action(1, RaiseTo(2))
    assert hand.current_player == 0
    assert hand.legal_actions(0) == (Fold(), Call())


def test_engine_rejects_illegal_out_of_turn_and_post_terminal_actions() -> None:
    hand = make_hand()
    with pytest.raises(OutOfTurnError):
        hand.apply_action(1, Check())
    with pytest.raises(IllegalActionError):
        hand.apply_action(0, Call())
    hand.apply_action(0, Check())
    hand.apply_action(1, Check())
    with pytest.raises(HandFinishedError):
        hand.apply_action(0, Check())


def test_same_seed_deals_same_cards() -> None:
    left = make_hand(seed=123)
    right = make_hand(seed=123)
    assert left.observe(0).private_cards == right.observe(0).private_cards
    assert left.observe(1).private_cards == right.observe(1).private_cards

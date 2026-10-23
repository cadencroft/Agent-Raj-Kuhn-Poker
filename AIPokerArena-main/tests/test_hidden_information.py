from dataclasses import fields

from arena.games.kuhn import KuhnHand


def test_observation_contains_only_the_viewers_card_and_no_private_attributes() -> None:
    hand = KuhnHand(("alice", "bob"), seed=91, hand_id="hidden-test")
    alice = hand.observe(0)
    bob = hand.observe(1)

    assert alice.private_cards != bob.private_cards
    assert bob.private_cards[0] not in repr(alice)
    assert alice.private_cards[0] not in repr(bob)
    assert len(alice.private_cards) == 1
    assert alice.toy_private_card == alice.private_cards[0]
    assert alice.board_cards == ()
    assert not hasattr(alice, "__dict__")

    field_names = {field.name for field in fields(alice)}
    forbidden = {
        "state",
        "deck",
        "rng",
        "engine",
        "table",
        "undealt_card",
        "opponent_cards",
        "future_cards",
    }
    assert field_names.isdisjoint(forbidden)
    assert all(not name.startswith("_") for name in field_names)


def test_observation_history_is_a_fresh_immutable_snapshot() -> None:
    hand = KuhnHand(("alice", "bob"), seed=1, hand_id="snapshot-test")
    before = hand.observe(0)
    hand.apply_action(0, hand.legal_actions(0)[0])
    after = hand.observe(0)
    assert before.action_history == ()
    assert len(after.action_history) == 1

from dataclasses import fields

import pytest

from arena import Action, Observation
from arena.baselines import SimpleKuhnRulesAgent
from arena.gui import KuhnGuiController


def test_gui_view_is_sanitized_and_only_offers_legal_actions() -> None:
    controller = KuhnGuiController(SimpleKuhnRulesAgent(), seed=42)
    view = controller.view()

    assert view.private_cards[0] in {"J", "Q", "K"}
    assert view.opponent_revealed_cards == ()
    assert {action.action_id for action in view.legal_actions} == {
        "check",
        "raise_to:2",
    }
    assert "opponent_private_cards" not in {field.name for field in fields(view)}
    assert not view.hand_complete


def test_gui_rejects_forged_and_out_of_sequence_actions() -> None:
    controller = KuhnGuiController(SimpleKuhnRulesAgent(), seed=42)
    with pytest.raises(ValueError, match="not currently legal"):
        controller.submit_action("call")
    with pytest.raises(ValueError, match="Finish the current hand"):
        controller.next_hand()


def test_gui_can_complete_showdown_and_start_next_hand() -> None:
    controller = KuhnGuiController(SimpleKuhnRulesAgent(), seed=42)
    view = controller.submit_action("check")
    if not view.hand_complete:
        legal_ids = {action.action_id for action in view.legal_actions}
        assert legal_ids == {"fold", "call"}
        view = controller.submit_action("call")

    assert view.hand_complete
    assert view.result_message is not None
    assert len(view.opponent_revealed_cards) == 1
    next_view = controller.next_hand()
    assert next_view.hand_number == 2
    assert not next_view.hand_complete
    assert next_view.opponent_revealed_cards == ()


def test_bot_receives_only_public_observations() -> None:
    class InspectingAgent:
        def __init__(self) -> None:
            self.observations: list[Observation] = []

        def new_hand(self, observation: Observation) -> None:
            self.observations.append(observation)

        def act(
            self,
            observation: Observation,
            legal_actions: tuple[Action, ...],
        ) -> Action:
            self.observations.append(observation)
            return legal_actions[0]

    bot = InspectingAgent()
    controller = KuhnGuiController(bot, seed=9)
    controller.submit_action("check")
    assert bot.observations
    assert all(len(observation.private_cards) == 1 for observation in bot.observations)
    assert all(not hasattr(observation, "deck") for observation in bot.observations)

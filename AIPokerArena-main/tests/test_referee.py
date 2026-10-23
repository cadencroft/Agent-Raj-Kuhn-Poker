import time

from arena import Action, Observation, RaiseTo
from arena.baselines import AlwaysFoldAgent, SimpleKuhnRulesAgent
from arena.match import run_kuhn_match


class InvalidAgent:
    def act(
        self,
        observation: Observation,
        legal_actions: tuple[Action, ...],
    ) -> Action:
        del observation, legal_actions
        return RaiseTo(999)


class CrashingAgent:
    def act(
        self,
        observation: Observation,
        legal_actions: tuple[Action, ...],
    ) -> Action:
        del observation, legal_actions
        raise RuntimeError("student bug")


class SlowAgent:
    def act(
        self,
        observation: Observation,
        legal_actions: tuple[Action, ...],
    ) -> Action:
        del observation
        time.sleep(0.05)
        return legal_actions[0]


def test_invalid_actions_are_counted_and_do_not_abort_match() -> None:
    result = run_kuhn_match(
        {"bad": InvalidAgent(), "safe": AlwaysFoldAgent()}, hands=4, seed=3
    )
    assert result.invalid_actions[0] > 0
    assert result.timeouts == (0, 0)
    assert sum(result.total_payouts) == 0


def test_crashes_are_counted_and_do_not_abort_match() -> None:
    result = run_kuhn_match(
        {"bad": CrashingAgent(), "safe": AlwaysFoldAgent()}, hands=4, seed=3
    )
    assert result.crashes[0] > 0
    assert sum(result.total_payouts) == 0


def test_timeouts_are_counted_and_do_not_abort_match() -> None:
    result = run_kuhn_match(
        {"slow": SlowAgent(), "safe": AlwaysFoldAgent()},
        hands=2,
        seed=3,
        action_timeout_seconds=0.005,
    )
    assert result.timeouts[0] > 0
    assert sum(result.total_payouts) == 0


def test_match_is_reproducible_and_seat_balanced() -> None:
    class SeatTrackingAgent(SimpleKuhnRulesAgent):
        def __init__(self) -> None:
            self.seats: list[int] = []

        def new_hand(self, observation: Observation) -> None:
            self.seats.append(observation.seat)

    left = SeatTrackingAgent()
    right = SeatTrackingAgent()
    first = run_kuhn_match({"a": left, "b": right}, hands=10, seed=72)
    second = run_kuhn_match(
        {"a": SimpleKuhnRulesAgent(), "b": SimpleKuhnRulesAgent()},
        hands=10,
        seed=72,
    )
    assert first.total_payouts == second.total_payouts
    assert left.seats.count(0) == left.seats.count(1) == 5
    assert right.seats.count(0) == right.seats.count(1) == 5

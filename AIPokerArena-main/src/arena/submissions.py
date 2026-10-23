"""Loading and in-process validation for student submissions."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from arena.api.actions import Action, action_to_dict
from arena.api.observation import Observation
from arena.api.results import HandResult, MatchContext, MatchResult
from arena.baselines import SimpleKuhnRulesAgent
from arena.match.referee import AgentLike
from arena.match.runner import run_kuhn_match


class SubmissionError(Exception):
    """A submission does not satisfy the documented contract."""


@dataclass(frozen=True, slots=True)
class LoadedSubmission:
    path: Path
    metadata: dict[str, Any]
    agent: object

    @property
    def display_name(self) -> str:
        value = self.metadata.get("agent_name") or self.path.name
        return str(value)


@dataclass(frozen=True, slots=True)
class ValidationReport:
    checks: tuple[tuple[str, bool, str], ...]

    @property
    def passed(self) -> bool:
        return all(passed for _, passed, _ in self.checks)


def load_submission(path: str | Path) -> LoadedSubmission:
    """Import ``agent.py`` and call its zero-argument ``create_agent`` factory."""
    directory = Path(path).expanduser().resolve()
    agent_file = directory / "agent.py"
    if not directory.is_dir():
        raise SubmissionError(f"Submission directory does not exist: {directory}")
    if not agent_file.is_file():
        raise SubmissionError(f"Submission is missing {agent_file.name}")

    metadata = _load_metadata(directory / "metadata.json")
    digest = hashlib.sha256(str(directory).encode()).hexdigest()[:16]
    module_name = f"arena_student_{digest}"
    spec = importlib.util.spec_from_file_location(module_name, agent_file)
    if spec is None or spec.loader is None:
        raise SubmissionError(f"Could not load module from {agent_file}")
    module = importlib.util.module_from_spec(spec)
    _execute_module(module, spec.loader, directory, module_name)

    factory = getattr(module, "create_agent", None)
    if not callable(factory):
        raise SubmissionError("agent.py must define callable create_agent()")
    try:
        agent = factory()
    except Exception as exc:
        raise SubmissionError(f"create_agent() failed: {exc}") from exc
    if not callable(getattr(agent, "act", None)):
        raise SubmissionError("create_agent() returned an object without act()")
    return LoadedSubmission(path=directory, metadata=metadata, agent=agent)


def validate_submission(
    path: str | Path,
    *,
    hands: int = 30,
    timeout_seconds: float = 0.1,
) -> ValidationReport:
    """Load a submission and exercise its public contract over repeated hands."""
    checks: list[tuple[str, bool, str]] = []
    try:
        loaded = load_submission(path)
    except SubmissionError as exc:
        return ValidationReport((("submission loads", False, str(exc)),))

    checks.extend(
        [
            ("submission imports", True, str(loaded.path / "agent.py")),
            ("create_agent exists", True, "factory returned an agent"),
            ("agent initializes", True, type(loaded.agent).__name__),
        ]
    )
    baseline_name = "SimpleRules"
    if loaded.display_name == baseline_name:
        baseline_name = "CourseSimpleRules"
    checked_agent = _ValidationAgent(loaded.agent)
    result = run_kuhn_match(
        {loaded.display_name: checked_agent, baseline_name: SimpleKuhnRulesAgent()},
        hands=hands,
        seed=2027,
        action_timeout_seconds=timeout_seconds,
    )
    index = result.players.index(loaded.display_name)
    checks.extend(
        [
            (
                "legal actions are returned",
                result.invalid_actions[index] == 0,
                f"{result.invalid_actions[index]} invalid action(s)",
            ),
            (
                "observation is not mutated",
                checked_agent.observation_mutations == 0,
                f"{checked_agent.observation_mutations} mutation(s)",
            ),
            (
                "action deadline is respected",
                result.timeouts[index] == 0,
                f"{result.timeouts[index]} timeout(s)",
            ),
            (
                "agent survives repeated hands",
                result.crashes[index] == 0,
                f"{result.crashes[index]} crash(es)",
            ),
            (
                "zero-sum accounting holds",
                sum(result.total_payouts) == 0,
                f"aggregate payouts: {result.total_payouts}",
            ),
        ]
    )

    second_load = load_submission(path)
    second_agent = _ValidationAgent(second_load.agent)
    second_result = run_kuhn_match(
        {
            second_load.display_name: second_agent,
            baseline_name: SimpleKuhnRulesAgent(),
        },
        hands=hands,
        seed=2027,
        action_timeout_seconds=timeout_seconds,
    )
    deterministic = (
        checked_agent.action_trace == second_agent.action_trace
        and result.total_payouts == second_result.total_payouts
    )
    checks.append(
        (
            "deterministic mode works",
            deterministic,
            "same seed produced the same decisions"
            if deterministic
            else "same seed produced different decisions",
        )
    )
    return ValidationReport(tuple(checks))


class _ValidationAgent:
    """Observe behavior without granting the submission any extra capabilities."""

    def __init__(self, delegate: object) -> None:
        self.delegate = delegate
        self.observation_mutations = 0
        self.action_trace: list[str] = []

    def new_match(self, context: MatchContext) -> None:
        self._call_optional("new_match", context)

    def new_hand(self, observation: Observation) -> None:
        snapshot = deepcopy(observation)
        try:
            self._call_optional("new_hand", observation)
        finally:
            if observation != snapshot:
                self.observation_mutations += 1

    def act(
        self,
        observation: Observation,
        legal_actions: tuple[Action, ...],
    ) -> Action:
        snapshot = deepcopy(observation)
        callback = cast(AgentLike, self.delegate).act
        try:
            candidate = callback(observation, legal_actions)
        finally:
            if observation != snapshot:
                self.observation_mutations += 1
        self.action_trace.append(_action_key(candidate))
        return candidate

    def hand_finished(self, result: HandResult) -> None:
        self._call_optional("hand_finished", result)

    def match_finished(self, result: MatchResult) -> None:
        self._call_optional("match_finished", result)

    def _call_optional(self, callback_name: str, value: object) -> None:
        callback = getattr(self.delegate, callback_name, None)
        if callable(callback):
            callback(value)


def _action_key(candidate: object) -> str:
    if isinstance(candidate, Action):
        try:
            return json.dumps(action_to_dict(candidate), sort_keys=True)
        except TypeError:
            pass
    return type(candidate).__qualname__


def _load_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SubmissionError(f"Invalid metadata.json: {exc}") from exc
    if not isinstance(value, dict):
        raise SubmissionError("metadata.json must contain a JSON object")
    return value


def _execute_module(
    module: ModuleType,
    loader: Any,
    directory: Path,
    module_name: str,
) -> None:
    old_path = list(sys.path)
    sys.path.insert(0, str(directory))
    sys.modules[module_name] = module
    try:
        loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        raise SubmissionError(f"Importing agent.py failed: {exc}") from exc
    finally:
        sys.path[:] = old_path

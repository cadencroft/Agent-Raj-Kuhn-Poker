"""Poker-domain actions exposed to agents."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Action:
    """Marker base class for all public actions."""


@dataclass(frozen=True, slots=True)
class Fold(Action):
    """Surrender the current hand."""


@dataclass(frozen=True, slots=True)
class Check(Action):
    """Pass without adding chips."""


@dataclass(frozen=True, slots=True)
class Call(Action):
    """Match the current wager."""


@dataclass(frozen=True, slots=True)
class RaiseTo(Action):
    """Raise total chips committed in the round to ``amount``."""

    amount: int


def action_name(action: Action) -> str:
    """Return the wire-format name for an action."""
    if isinstance(action, Fold):
        return "fold"
    if isinstance(action, Check):
        return "check"
    if isinstance(action, Call):
        return "call"
    if isinstance(action, RaiseTo):
        return "raise_to"
    raise TypeError(f"Unknown action type: {type(action).__name__}")


def action_to_dict(action: Action) -> dict[str, Any]:
    """Serialize an action without exposing implementation details."""
    result: dict[str, Any] = {"type": action_name(action)}
    if isinstance(action, RaiseTo):
        result["amount"] = action.amount
    return result


def format_action(action: Action) -> str:
    """Human-readable action label used by the CLI."""
    if isinstance(action, RaiseTo):
        return f"raise to {action.amount}"
    return action_name(action)

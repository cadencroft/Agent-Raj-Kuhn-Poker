"""Small shared exceptions for authoritative games."""


class GameError(Exception):
    """Base class for errors raised by a game implementation."""


class IllegalActionError(GameError):
    """Raised when an action is not legal in the current state."""


class OutOfTurnError(GameError):
    """Raised when the wrong seat tries to act."""


class HandFinishedError(GameError):
    """Raised when code tries to modify a completed hand."""

"""Best-effort in-process action deadlines for development matches."""

from __future__ import annotations

import signal
import threading
import time
from collections.abc import Callable


class ActionTimeoutError(TimeoutError):
    """Raised when an agent exceeds its action deadline."""


def call_with_timeout[T](function: Callable[[], T], timeout_seconds: float) -> T:
    """Call ``function`` with a real deadline when supported.

    POSIX main-thread execution uses ``setitimer`` and can interrupt a stuck
    Python agent. Other environments still measure and reject late responses.
    Tournament-grade isolation belongs in the future subprocess runner.
    """
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    can_interrupt = (
        threading.current_thread() is threading.main_thread()
        and hasattr(signal, "SIGALRM")
        and hasattr(signal, "setitimer")
    )
    if not can_interrupt:
        started = time.monotonic()
        result = function()
        if time.monotonic() - started > timeout_seconds:
            raise ActionTimeoutError(
                f"Agent exceeded {timeout_seconds:.3f}s action deadline"
            )
        return result

    def handle_alarm(signum: int, frame: object) -> None:
        del signum, frame
        raise ActionTimeoutError(
            f"Agent exceeded {timeout_seconds:.3f}s action deadline"
        )

    old_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, handle_alarm)
    old_timer = signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        return function()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        if old_timer[0] > 0:
            signal.setitimer(signal.ITIMER_REAL, *old_timer)

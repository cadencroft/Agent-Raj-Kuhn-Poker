"""JSONL replay persistence."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, TextIO


class ReplayWriter:
    """Append complete hand records as one JSON object per line."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file: TextIO = self.path.open("a", encoding="utf-8")

    def write(self, record: Mapping[str, Any]) -> None:
        self._file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
        self._file.write("\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> ReplayWriter:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def load_replays(path: str | Path) -> Iterator[dict[str, Any]]:
    """Yield validated top-level JSON objects from a replay JSONL file."""
    with Path(path).open(encoding="utf-8") as replay_file:
        for line_number, line in enumerate(replay_file, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"Replay line {line_number} is not a JSON object")
            yield value

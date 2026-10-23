"""Public checks for the submission contract.

These tests check correctness and compatibility, not playing strength. Instructors
may run additional private tests when grading.
"""

import json
from pathlib import Path

from arena.submissions import load_submission, validate_submission

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_metadata_has_required_fields() -> None:
    metadata = json.loads(
        (REPOSITORY_ROOT / "metadata.json").read_text(encoding="utf-8")
    )

    for field in ("team", "agent_name", "version"):
        assert isinstance(metadata.get(field), str), f"{field} must be a string"
        assert metadata[field].strip(), f"{field} must not be empty"

    authors = metadata.get("authors")
    assert isinstance(authors, list), "authors must be a list"
    assert authors, "authors must contain at least one name"
    assert all(isinstance(author, str) and author.strip() for author in authors)


def test_factory_creates_an_agent() -> None:
    loaded = load_submission(REPOSITORY_ROOT)
    assert callable(getattr(loaded.agent, "act", None))


def test_agent_passes_arena_validation() -> None:
    report = validate_submission(REPOSITORY_ROOT, hands=30, timeout_seconds=0.1)
    failures = [
        f"{name}: {detail}" for name, passed, detail in report.checks if not passed
    ]
    assert report.passed, "\n".join(failures)

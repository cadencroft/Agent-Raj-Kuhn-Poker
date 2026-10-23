from pathlib import Path

from arena.submissions import load_submission, validate_submission


def make_submission(path: Path, source: str) -> Path:
    path.mkdir()
    (path / "agent.py").write_text(source)
    (path / "metadata.json").write_text(
        '{"agent_name": "StudentAgent", "team": "Test Team"}'
    )
    return path


def test_submission_loader_accepts_structural_agent(tmp_path) -> None:
    path = make_submission(
        tmp_path / "student",
        """
class Agent:
    def act(self, observation, legal_actions):
        return legal_actions[0]

def create_agent():
    return Agent()
""",
    )
    loaded = load_submission(path)
    assert loaded.display_name == "StudentAgent"
    assert type(loaded.agent).__name__ == "Agent"
    assert validate_submission(path, hands=8).passed


def test_submission_validator_reports_invalid_agent(tmp_path) -> None:
    path = make_submission(
        tmp_path / "student",
        """
class Agent:
    def act(self, observation, legal_actions):
        return object()

def create_agent():
    return Agent()
""",
    )
    report = validate_submission(path, hands=4)
    assert not report.passed
    assert any(
        name == "legal actions are returned" and not ok for name, ok, _ in report.checks
    )


def test_submission_validator_detects_observation_mutation(tmp_path) -> None:
    path = make_submission(
        tmp_path / "student",
        """
class Agent:
    def act(self, observation, legal_actions):
        object.__setattr__(observation, "pot", 999)
        return legal_actions[0]

def create_agent():
    return Agent()
""",
    )
    report = validate_submission(path, hands=4)
    assert any(
        name == "observation is not mutated" and not ok for name, ok, _ in report.checks
    )

"""Run a short deterministic match without installing the CLI entry point."""

from arena.baselines import RandomAgent, SimpleKuhnRulesAgent
from arena.match import run_kuhn_match


def main() -> None:
    result = run_kuhn_match(
        {"random": RandomAgent(), "rules": SimpleKuhnRulesAgent()},
        hands=100,
        seed=42,
    )
    print(result)


if __name__ == "__main__":
    main()

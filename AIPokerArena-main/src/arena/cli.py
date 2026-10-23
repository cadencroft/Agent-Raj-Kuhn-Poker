"""Command-line interface for playing, validating, and inspecting Kuhn games."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

from arena.baselines import RandomAgent, SimpleKuhnRulesAgent
from arena.gui import KuhnGuiController, serve_gui
from arena.match.referee import AgentLike
from arena.match.replay import load_replays
from arena.match.runner import run_kuhn_match
from arena.submissions import SubmissionError, load_submission, validate_submission
from arena.tournament import run_round_robin


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arena",
        description="Run and grade poker-playing agents.",
    )
    parser.add_argument("--verbose", action="store_true", help="show referee logs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    test_parser = subparsers.add_parser("test", help="validate a submission")
    test_parser.add_argument("submission", type=Path)
    test_parser.add_argument("--hands", type=int, default=30)
    test_parser.add_argument("--timeout-ms", type=float, default=100.0)

    play_parser = subparsers.add_parser("play", help="play a heads-up match")
    play_parser.add_argument("agent_a", help="submission path, 'random', or 'simple'")
    play_parser.add_argument("agent_b", help="submission path, 'random', or 'simple'")
    play_parser.add_argument("--game", choices=("kuhn",), default="kuhn")
    play_parser.add_argument("--hands", type=int, default=1000)
    play_parser.add_argument("--seed", type=int, default=42)
    play_parser.add_argument("--timeout-ms", type=float, default=100.0)
    play_parser.add_argument("--replay", type=Path)

    human_parser = subparsers.add_parser(
        "play-human", help="play Kuhn poker against an agent in a local browser"
    )
    human_parser.add_argument("agent", help="submission path, 'random', or 'simple'")
    human_parser.add_argument("--game", choices=("kuhn",), default="kuhn")
    human_parser.add_argument("--seed", type=int, default=42)
    human_parser.add_argument("--timeout-ms", type=float, default=100.0)
    human_parser.add_argument("--port", type=int, default=8000)
    human_parser.add_argument("--no-open", action="store_true")

    tournament_parser = subparsers.add_parser(
        "tournament", help="run a round robin over submission directories"
    )
    tournament_parser.add_argument("submissions", type=Path)
    tournament_parser.add_argument("--game", choices=("kuhn",), default="kuhn")
    tournament_parser.add_argument("--hands", type=int, default=1000)
    tournament_parser.add_argument("--seed", type=int, default=42)
    tournament_parser.add_argument("--timeout-ms", type=float, default=100.0)

    replay_parser = subparsers.add_parser("replay", help="inspect a JSONL replay")
    replay_parser.add_argument("path", type=Path)
    replay_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.ERROR,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        if args.command == "test":
            return _test_command(args)
        if args.command == "play":
            return _play_command(args)
        if args.command == "play-human":
            return _play_human_command(args)
        if args.command == "tournament":
            return _tournament_command(args)
        if args.command == "replay":
            return _replay_command(args)
    except (OSError, ValueError, SubmissionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"Unhandled command: {args.command}")


def _test_command(args: argparse.Namespace) -> int:
    report = validate_submission(
        args.submission,
        hands=args.hands,
        timeout_seconds=args.timeout_ms / 1000.0,
    )
    for name, passed, detail in report.checks:
        mark = "✓" if passed else "✗"
        print(f"{mark} {name}: {detail}")
    return 0 if report.passed else 1


def _play_command(args: argparse.Namespace) -> int:
    name_a, agent_a = _resolve_agent(args.agent_a)
    name_b, agent_b = _resolve_agent(args.agent_b)
    if name_a == name_b:
        name_a = f"{name_a}-1"
        name_b = f"{name_b}-2"
    result = run_kuhn_match(
        {name_a: agent_a, name_b: agent_b},
        hands=args.hands,
        seed=args.seed,
        action_timeout_seconds=args.timeout_ms / 1000.0,
        replay_path=args.replay,
    )
    print(f"Kuhn match: {result.hands} hands, seed {result.seed}")
    print("player               chips   chips/100  timeout  invalid  crashes")
    for index, name in enumerate(result.players):
        chips = result.total_payouts[index]
        rate = chips * 100.0 / result.hands
        print(
            f"{name[:20]:20} {chips:7d} {rate:11.2f} "
            f"{result.timeouts[index]:8d} {result.invalid_actions[index]:8d} "
            f"{result.crashes[index]:8d}"
        )
    if args.replay is not None:
        print(f"Replay: {args.replay}")
    return 0


def _tournament_command(args: argparse.Namespace) -> int:
    root = args.submissions.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Submission directory does not exist: {root}")
    submission_paths = sorted(
        path.parent for path in root.glob("*/agent.py") if path.is_file()
    )
    if len(submission_paths) < 2:
        raise ValueError(f"Expected at least two submissions directly under {root}")

    factories: dict[str, Callable[[], object]] = {}
    for path in submission_paths:
        first_load = load_submission(path)
        name = first_load.display_name
        if name in factories:
            raise ValueError(f"Duplicate agent name: {name!r}")
        factories[name] = _make_submission_factory(path)

    tournament = run_round_robin(
        factories,
        hands_per_matchup=args.hands,
        seed=args.seed,
        action_timeout_seconds=args.timeout_ms / 1000.0,
    )
    print(
        f"Kuhn round robin: {len(tournament.matches)} matchups, "
        f"{args.hands} hands each, seed {args.seed}"
    )
    print("rank player               hands   chips  chips/100  faults")
    for rank, standing in enumerate(tournament.standings, start=1):
        faults = standing.timeouts + standing.invalid_actions + standing.crashes
        print(
            f"{rank:4d} {standing.player_id[:20]:20} {standing.hands:7d} "
            f"{standing.total_chips:7d} {standing.chips_per_100:10.2f} "
            f"{faults:7d}"
        )
    return 0


def _play_human_command(args: argparse.Namespace) -> int:
    name, agent = _resolve_agent(args.agent)
    controller = KuhnGuiController(
        cast(AgentLike, agent),
        bot_id=name,
        seed=args.seed,
        action_timeout_seconds=args.timeout_ms / 1000.0,
    )
    serve_gui(controller, port=args.port, open_browser=not args.no_open)
    return 0


def _replay_command(args: argparse.Namespace) -> int:
    count = 0
    for record in load_replays(args.path):
        count += 1
        if args.json:
            print(json.dumps(record, indent=2, sort_keys=True))
            continue
        players = record.get("players", [])
        cards = record.get("private_cards", [])
        payouts = record.get("payouts", [])
        print(
            f"{record.get('hand_id')}: seed={record.get('seed')} "
            f"players={players} cards={cards} payouts={payouts}"
        )
        for event in record.get("events", []):
            if event.get("type") == "action":
                suffix = ""
                if "substituted_for" in event:
                    suffix = f" (fallback: {event['substituted_for']})"
                print(
                    f"  seat {event['seat']} {event['player_id']}: "
                    f"{event['action']}{suffix}"
                )
    if count == 0:
        raise ValueError("Replay contains no hand records")
    return 0


def _resolve_agent(reference: str) -> tuple[str, object]:
    normalized = reference.lower()
    if normalized == "random":
        return "Random", RandomAgent()
    if normalized == "simple":
        return "SimpleRules", SimpleKuhnRulesAgent()
    loaded = load_submission(reference)
    return loaded.display_name, loaded.agent


def _make_submission_factory(path: Path) -> Callable[[], object]:
    def factory() -> object:
        return load_submission(path).agent

    return factory


if __name__ == "__main__":
    raise SystemExit(main())

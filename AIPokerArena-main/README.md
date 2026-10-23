# AI Poker Arena

AI Poker Arena is a small teaching environment where students submit poker agents
through one stable, poker-shaped API. The current MVP implements deterministic,
heads-up **Kuhn poker** and establishes the boundaries later games can reuse.

## What is included

- Immutable student-facing observations and action value objects
- An authoritative Kuhn state machine with no hidden-state references in observations
- A referee that validates every action and survives invalid actions, crashes, and
  action timeouts
- Deterministic hand seeds, alternating seats, zero-sum settlement, and JSONL replay
- A `create_agent()` submission loader and validator
- Random and deliberately simple rule-based baselines
- Heads-up play, round-robin tournament, submission test, and replay CLI commands
- A dependency-free localhost browser GUI for human-vs-agent Kuhn play
- Tests for game rules, accounting, determinism, seat balance, and hidden information

This first version deliberately runs student code in-process for easy debugging.
That is suitable for development, **not for adversarial tournament security**. A
subprocess/Docker runner is the next trust-boundary milestone.

## Kuhn poker rules

Kuhn poker has a three-card deck: `J`, `Q`, and `K`. Two players each ante one chip
and receive one private card. One card remains undealt. There is one betting round
with a fixed one-chip bet:

1. Player 0 checks or bets.
2. After a check, player 1 checks or bets.
3. A player facing a bet folds or calls.
4. At showdown, the higher card wins.

A check/check showdown is worth one net chip; a called bet is worth two. A player
winning after a fold earns one net chip.

## Setup

Python 3.12 or newer is required. With `uv`:

```bash
uv sync --extra dev
uv run pytest
```

Or with a conventional virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```

## Write an agent

A submission is a directory containing `agent.py` and, preferably,
`metadata.json`:

```text
my_submission/
├── agent.py
└── metadata.json
```

`agent.py` exports a factory. Subclassing is optional:

```python
from arena import Call, Check, Fold, RaiseTo


class MyAgent:
    def act(self, observation, legal_actions):
        card = observation.toy_private_card

        if card == "K":
            for action in legal_actions:
                if isinstance(action, (RaiseTo, Call)):
                    return action

        for action in legal_actions:
            if isinstance(action, (Check, Fold)):
                return action

        return legal_actions[0]


def create_agent():
    return MyAgent()
```

The essential contract is:

```python
agent.act(observation, legal_actions) -> Action
```

Return one of the supplied legal action values. `Observation` is immutable and
contains the acting player's private card plus public state—never the opponent's
card, undealt card, deck, RNG, or game object.

See [`examples/kuhn_if_else/agent.py`](examples/kuhn_if_else/agent.py) for a
complete first-week example.

## Commands

Validate a submission over repeated hands:

```bash
uv run arena test ./examples/kuhn_if_else
```

Play against a built-in baseline and save an instructor replay:

```bash
uv run arena play ./examples/kuhn_if_else random \
  --game kuhn --hands 1000 --seed 42 \
  --replay data/replays/example.jsonl
```

Inspect it:

```bash
uv run arena replay data/replays/example.jsonl
```

Play against a submission in the browser (the server binds only to localhost):

```bash
uv run arena play-human ./examples/kuhn_if_else --game kuhn --seed 42
```

Run every immediate child submission directory against every other one:

```bash
uv run arena tournament ./submissions --game kuhn --hands 10000 --seed 42
```

`--hands` on the tournament command means hands per pair. Every heads-up match
alternates seats. Results report net chips per 100 hands plus timeout, invalid
action, and crash counts.

## Reproducibility and replay visibility

A master match seed deterministically generates a seed for every hand. Replays
record seats, full dealt cards, the undealt card, legal actions, accepted actions,
fallbacks, and payouts. Consequently replay files are **instructor/debug
artifacts** and should not be exposed to agents during a live match. Agent-facing
`HandResult` reveals cards only at showdown.

Given the same arena version, match seed, policies, and policy randomness, the same
actions and outcomes are produced. The packaged `RandomAgent` derives its own RNG
seed from the public match seed and player ID.

## Project map

```text
src/arena/api/          stable student-facing types
src/arena/games/        authoritative game state
src/arena/match/        referee, runner, timeouts, replay
src/arena/tournament/   round-robin scheduling and standings
src/arena/gui/          sanitized controller, view models, and local web UI
src/arena/submissions.py
baselines/              submission-shaped course baselines
examples/               student-readable examples
tests/                  rules, security, and invariant tests
```

The recommended next milestone is subprocess isolation using newline-delimited
JSON, followed by a browser GUI that pauses the same referee at human decisions.

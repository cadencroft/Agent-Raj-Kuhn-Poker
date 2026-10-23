# Poker Agent Submission

> **Assignment:** Your instructor will replace this block with the goals, rules,
> allowed dependencies, grading rubric, and due date for this assignment.

Build a runnable poker-playing agent for the
[AI Poker Arena](https://github.com/grieggs/AIPokerArena). The referee owns the
game state. Your code receives a safe, immutable observation and a tuple of legal
actions; it must return one of those actions before the deadline.

## What to edit

- Implement your strategy in `agent.py`. You may add more Python files, but keep
  the zero-argument `create_agent()` factory in `agent.py`.
- Replace every `CHANGE ME` value in `metadata.json`.
- If your agent needs third-party runtime packages, add them to
  `requirements.txt`. Follow any assignment-specific dependency restrictions.
- Do not edit the public tests merely to make a broken agent appear to pass.

The required call is:

```python
agent.act(observation, legal_actions) -> Action
```

Return one of the action objects in `legal_actions`. Do not construct an action
that was not offered, mutate the observation, inspect arena internals, or use
uncontrolled global randomness.

## Set up your environment

Install [uv](https://docs.astral.sh/uv/), then run:

```bash
uv venv --python 3.12
uv pip install -r requirements-dev.txt
```

Activate the environment if you want to run Python directly:

```bash
source .venv/bin/activate       # macOS/Linux
.venv\Scripts\activate          # Windows PowerShell
```

## Check your submission

Run the student validation script before every submission:

```bash
uv run python validate_submission.py
```

The script runs code-quality checks, the public test suite, and the arena contract
validator. It checks that the submission imports, creates an agent, returns legal
actions, does not mutate observations, meets the action deadline, survives repeated
hands, preserves zero-sum accounting, and behaves deterministically when rerun with
the same seed. It exits with a nonzero status when any check fails, so the final
line should read `All submission checks passed.`

You may still run an individual check while debugging:

```bash
uv run ruff check .
uv run pytest
uv run arena test .
```

For Kuhn assignments, play against a baseline:

```bash
uv run arena play . random --game kuhn --hands 1000 --seed 42
uv run arena play . simple --game kuhn --hands 1000 --seed 42
```

You can also play against your agent in a local browser:

```bash
uv run arena play-human . --game kuhn --seed 42
```

## Useful public API

Import public types from `arena`, for example:

```python
from arena import Action, Call, Check, Fold, Observation, PokerAgent, RaiseTo
```

For Kuhn poker, `observation.toy_private_card` is `"J"`, `"Q"`, or `"K"`.
Useful public fields also include `player_id`, `seat`, `pot`, `amount_to_call`,
`players`, and `action_history`. Treat the observation as read-only. Never expect
access to an opponent's private card, the undealt card, deck order, RNG, or the
authoritative game object.

Optional lifecycle methods are available when your agent needs memory:

```python
def new_match(self, context): ...
def new_hand(self, observation): ...
def hand_finished(self, result): ...
def match_finished(self, result): ...
```

## Submission checklist

- `metadata.json` identifies your team, agent, version, and authors.
- `create_agent()` takes no arguments and returns a fresh agent.
- Every call to `act()` returns one of the supplied legal actions.
- The observation is not mutated and no hidden engine state is accessed.
- Any runtime dependencies are listed in `requirements.txt`.
- `uv run python validate_submission.py` reports that every check passed.
- Your final work is committed and pushed before the deadline.

The validation checks establish compatibility, not strategy quality. Your
instructor may run additional private tests and tournament matches.

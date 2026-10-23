# AGENTS.md — AI Poker Arena

## Project purpose

Build a college-level AI teaching environment in which student teams develop poker-playing agents throughout a semester.

The course is built around *Artificial Intelligence: A Modern Approach (AIMA)*. Students should begin with very simple hand-coded policies for Kuhn poker and progressively apply ideas from the course, including:

- rational agents
- utility-based decision making
- adversarial search
- probability and Bayesian reasoning
- imperfect-information games
- opponent modeling
- Monte Carlo methods
- reinforcement learning
- self-play
- counterfactual regret minimization (CFR)
- function approximation / neural methods

The final event is a class tournament using full-table Texas Hold'em agents.

The infrastructure must support this progression without requiring students to rewrite their agent interface for every assignment.

---

# Core design principles

1. **The referee owns the game.**
   Student agents never directly mutate authoritative game state.

2. **Agents see observations, not internal state.**
   Hidden cards, deck order, RNG state, and other privileged information must never be exposed to student code.

3. **One stable student-facing API.**
   The same basic `Agent` interface should work for:
   - Kuhn poker
   - Leduc poker
   - simplified Hold'em
   - full-table Hold'em

4. **Determinism matters.**
   Every match/hand must be reproducible from a recorded seed.

5. **Every action is logged.**
   We need complete replayability for grading, debugging, and tournament disputes.

6. **Student agents are untrusted code.**
   During development they may run in-process for convenience.
   Tournament execution should support process isolation and eventually Docker containers.

7. **Poker-specific public API, engine-specific internals.**
   Students should interact with friendly poker concepts, not PokerKit/OpenSpiel internals.

8. **Separate human-friendly and RL-friendly representations.**
   Student observations/actions should be readable.
   RL adapters may convert these into tensors, discrete action IDs, and action masks.

9. **Do not make notebooks the submission format.**
   Every assignment must produce a runnable agent.

10. **Prefer simple infrastructure over framework complexity.**
    The educational goal is AI, not distributed systems.

---

# Recommended technology

Primary language:

- Python 3.12+

Core tooling:

- `uv` for Python dependency/environment management
- `pytest` for tests
- `ruff` for formatting/linting
- `mypy` or `pyright` for static type checking
- `pydantic` only where runtime validation is genuinely useful
- standard-library `dataclasses` for most domain models

Poker/game infrastructure:

- PokerKit for authoritative poker rules and Hold'em simulation
- OpenSpiel for research/reference implementations, Kuhn/Leduc, CFR, exploitability, and imperfect-information algorithms

Optional later-stage tooling:

- NumPy
- PyTorch
- Gymnasium adapters
- Stable-Baselines3 where appropriate
- Docker for tournament isolation

Persistence:

- JSONL for hand and action logs
- SQLite for tournament metadata, standings, and summaries

Do not introduce Postgres, Redis, Kubernetes, Ray, Celery, Kafka, or similar infrastructure unless a concrete need emerges.

---

# Repository layout

Target structure:

```text
ai-poker-arena/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .python-version
│
├── src/
│   └── arena/
│       ├── __init__.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── agent.py
│       │   ├── actions.py
│       │   ├── observation.py
│       │   └── results.py
│       │
│       ├── games/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── kuhn.py
│       │   ├── leduc.py
│       │   └── holdem.py
│       │
│       ├── engines/
│       │   ├── __init__.py
│       │   ├── pokerkit_adapter.py
│       │   └── openspiel_adapter.py
│       │
│       ├── match/
│       │   ├── __init__.py
│       │   ├── referee.py
│       │   ├── runner.py
│       │   ├── timeout.py
│       │   └── replay.py
│       │
│       ├── tournament/
│       │   ├── __init__.py
│       │   ├── scheduler.py
│       │   ├── standings.py
│       │   ├── ratings.py
│       │   └── database.py
│       │
│       ├── rl/
│       │   ├── __init__.py
│       │   ├── encoding.py
│       │   ├── action_mask.py
│       │   ├── gymnasium_adapter.py
│       │   └── self_play.py
│       │
│       ├── sandbox/
│       │   ├── __init__.py
│       │   ├── subprocess_agent.py
│       │   ├── protocol.py
│       │   └── docker_agent.py
│       │
│       ├── gui/
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── controller.py
│       │   ├── human_agent.py
│       │   ├── view_models.py
│       │   └── assets/
│       │
│       └── cli.py
│
├── baselines/
│   ├── random_agent/
│   │   └── agent.py
│   ├── kuhn_rules_agent/
│   │   └── agent.py
│   └── calling_station/
│       └── agent.py
│
├── examples/
│   ├── kuhn_if_else/
│   ├── kuhn_mixed_strategy/
│   ├── leduc_bayes/
│   ├── cfr/
│   └── q_learning/
│
├── submissions/
│   └── .gitkeep
│
├── tests/
│   ├── test_agent_api.py
│   ├── test_hidden_information.py
│   ├── test_kuhn.py
│   ├── test_leduc.py
│   ├── test_holdem.py
│   ├── test_replay.py
│   ├── test_determinism.py
│   ├── test_timeouts.py
│   └── test_tournament.py
│
├── scripts/
│   ├── run_smoke_test.py
│   ├── generate_replay.py
│   └── benchmark_agents.py
│
└── data/
    ├── replays/
    └── arena.sqlite
```

Avoid creating deep abstractions until at least two concrete implementations require them.

---

# Student-facing API

The public API is the most important compatibility boundary in the project.

Keep it small.

## Agent interface

Start with:

```python
from abc import ABC, abstractmethod

class PokerAgent(ABC):
    def new_match(self, context: "MatchContext") -> None:
        pass

    def new_hand(self, observation: "Observation") -> None:
        pass

    @abstractmethod
    def act(
        self,
        observation: "Observation",
        legal_actions: tuple["Action", ...],
    ) -> "Action":
        raise NotImplementedError

    def hand_finished(self, result: "HandResult") -> None:
        pass

    def match_finished(self, result: "MatchResult") -> None:
        pass
```

Do not require students to subclass unless useful.
Structural compatibility is acceptable if testing remains straightforward.

The critical requirement is:

```python
agent.act(observation, legal_actions) -> Action
```

---

# Observation model

The agent must receive only player-visible information.

Use an immutable dataclass.

Example:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class PublicPlayerState:
    seat: int
    stack: int
    committed: int
    folded: bool
    all_in: bool

@dataclass(frozen=True)
class Observation:
    game: str

    hand_id: str
    player_id: str
    seat: int

    private_cards: tuple[str, ...]
    board_cards: tuple[str, ...]

    pot: int
    current_bet: int
    amount_to_call: int

    dealer_seat: int
    small_blind: int
    big_blind: int

    players: tuple[PublicPlayerState, ...]
    action_history: tuple["ObservedAction", ...]

    street: str

    # Optional fields for toy games such as Kuhn/Leduc.
    toy_private_card: Optional[str] = None
```

The observation API may evolve, but once an assignment is released, avoid breaking changes.

Prefer adding optional fields over changing meanings.

---

# Hidden-information firewall

This project MUST enforce imperfect information correctly.

Student code must never receive references to authoritative engine objects.

Never pass:

```python
state
deck
rng
engine
game
table
player_object
```

directly into student code.

Instead, construct a fresh immutable `Observation`.

Tests must explicitly verify that observations do not expose:

- opponent hole cards
- undealt cards
- deck ordering
- burn cards
- future board cards
- engine RNG state
- hidden game state through object references
- private attributes reachable by introspection from observation objects

Treat accidental hidden-state leakage as a critical bug.

---

# Actions

Use poker-domain action objects.

Recommended API:

```python
from dataclasses import dataclass

class Action:
    pass

@dataclass(frozen=True)
class Fold(Action):
    pass

@dataclass(frozen=True)
class Check(Action):
    pass

@dataclass(frozen=True)
class Call(Action):
    pass

@dataclass(frozen=True)
class RaiseTo(Action):
    amount: int
```

For early restricted-action assignments, legal actions may contain concrete raise choices:

```python
(
    Fold(),
    Call(),
    RaiseTo(40),
    RaiseTo(80),
    RaiseTo(200),
)
```

For full no-limit Hold'em, use a legal-range representation internally, but keep submission behavior simple.

Preferred public approach:

```python
@dataclass(frozen=True)
class LegalActionSet:
    can_fold: bool
    can_check: bool
    call_amount: int | None
    min_raise_to: int | None
    max_raise_to: int | None
```

However, the initial implementation may use an explicit tuple of actions until arbitrary bet sizing is introduced.

Do not expose raw engine action IDs to students.

---

# Kuhn poker implementation

Kuhn is the first course environment.

Goals:

- extremely simple agent API
- complete reproducibility
- fast tournaments
- easy strategy inspection
- compatibility with OpenSpiel for reference calculations

Initial allowed concepts for students should be simple Python:

- `if`
- `elif`
- `else`
- variables
- arithmetic
- random numbers

A baseline may look like:

```python
class KuhnRulesAgent:
    def act(self, observation, legal_actions):
        card = observation.toy_private_card

        if card == "K":
            return choose_bet_or_raise(legal_actions)

        if card == "J":
            return choose_check_or_fold(legal_actions)

        return choose_random_legal_action(legal_actions)
```

Provide:

- `RandomAgent`
- one deliberately mediocre rule-based agent
- deterministic test cases

Do NOT provide an optimal Kuhn implementation in the first assignment.

---

# Leduc poker

Use Leduc as the bridge between Kuhn and Hold'em.

Educational goals:

- multiple betting rounds
- public information arriving over time
- belief updating
- expected utility
- opponent modeling
- imperfect-information reasoning

Prefer using OpenSpiel as the reference implementation.

The course-facing observation API should remain substantially unchanged.

---

# Hold'em progression

Do not jump immediately from Kuhn to unrestricted no-limit Hold'em.

Implement stages.

## Stage 1 — Restricted Hold'em

Recommended:

- 6 players
- fixed stacks
- no antes
- standard blinds
- no rebuys during a scoring block
- discrete raise abstraction

Example actions:

- fold
- check/call
- half-pot raise
- pot-size raise
- all-in

The engine converts abstractions into legal raise amounts.

Document rounding behavior exactly.

## Stage 2 — Full no-limit Hold'em

Final tournament should support:

- 6 players per table
- arbitrary legal no-limit raise sizes
- correct side pots
- all-ins
- split pots
- ties
- standard Hold'em hand evaluation
- dealer/button movement
- blinds
- seat rotation
- deterministic deck generation from seed

PokerKit should be the default referee implementation unless a stronger reason emerges.

---

# Tournament philosophy

The tournament must measure agent quality more reliably than a single knockout bracket.

Primary evaluation should use repeated cash-game-style play.

Recommended structure:

1. Agents play many hands.
2. Rotate table positions.
3. Repeatedly reshuffle table composition.
4. Use deterministic seeds.
5. Record per-agent profit/loss.
6. Normalize results in big blinds.

Primary metric:

```text
bb / 100 hands
```

Also report:

- total hands
- total big blinds won/lost
- standard error or confidence estimate
- fold/call/raise frequencies
- showdown frequency
- timeout count
- illegal-action count
- crashes

Optional secondary metrics:

- Elo-like rating
- head-to-head matrix
- exploitability for games where calculable
- bankroll graph

The final theatrical event may be an elimination tournament, but do not use a single elimination event as the sole academic performance measure.

---

# Seat balancing

Poker position matters.

Tournament scheduling must rotate seats.

For a six-player table, avoid keeping agents in fixed positions.

At minimum, cyclically rotate:

```text
A B C D E F
F A B C D E
E F A B C D
D E F A B C
C D E F A B
B C D E F A
```

For larger tournaments, table assignment and seat assignment must both be randomized or balanced.

Store seat assignment in every hand record.

---

# Deterministic randomness

Every hand receives a seed.

All randomness must derive from controlled RNG instances.

Never use uncontrolled global randomness in authoritative game code.

Preferred:

```python
rng = random.Random(seed)
```

or an explicitly seeded NumPy generator.

A replay must contain enough information to reproduce:

- deck order
- player seats
- button
- blind structure
- starting stacks
- actions
- resulting payouts

---

# Replay format

Use JSONL or structured JSON.

A complete replay should include:

```json
{
  "hand_id": "...",
  "seed": 123456,
  "game": "nlhe",
  "players": ["team_a", "team_b", "team_c"],
  "button_seat": 2,
  "starting_stacks": [200, 200, 200],
  "events": [
    {
      "type": "deal_private",
      "seat": 0
    },
    {
      "type": "action",
      "seat": 0,
      "action": {
        "type": "raise_to",
        "amount": 6
      }
    }
  ],
  "board": ["As", "7h", "4d", "Tc", "2s"],
  "payouts": [18, -6, -12]
}
```

Student-visible logs must omit hidden cards until the hand is complete.

Instructor/debug replays may contain complete card information.

---

# Match runner

The referee loop should conceptually do:

```python
while not hand.finished:
    seat = hand.current_player
    observation = hand.observe(seat)
    legal_actions = hand.legal_actions(seat)

    action = agent_for(seat).act(
        observation,
        legal_actions,
    )

    hand.apply_action(seat, action)
```

The authoritative game object must validate every action.

Never trust an agent to return a legal move.

---

# Invalid actions

Define policy clearly and use it consistently.

Recommended:

1. Log the invalid action.
2. Increment that agent's fault counter.
3. Substitute a safe legal default.

Suggested fallback order:

```text
check
call
fold
```

depending on legality.

For repeated invalid actions, allow tournament configuration to:

- penalize score
- forfeit the hand
- forfeit the match
- disqualify the submission

Do not crash the entire tournament because one agent misbehaves.

---

# Time limits

Agents must have per-action time limits.

Development defaults may be generous.

Tournament defaults should be explicit.

Example:

```text
Kuhn:
100 ms/action

Leduc:
250 ms/action

Restricted Hold'em:
500 ms/action

Final Hold'em:
1–2 seconds/action
```

Exact values are instructor-configurable.

Timeout policy:

1. terminate/cancel the action request
2. log timeout
3. substitute safe legal action
4. continue tournament when possible

Keep track of cumulative compute if desired.

---

# Student submission contract

Every team submission should eventually have:

```text
submission/
├── agent.py
├── requirements.txt
└── metadata.json
```

Optional later:

```text
submission/
├── Dockerfile
├── agent.py
├── requirements.txt
├── model/
└── metadata.json
```

`metadata.json` example:

```json
{
  "team": "Team Rocket",
  "agent_name": "Bluffachu",
  "version": "1.0",
  "authors": [
    "Student One",
    "Student Two"
  ]
}
```

The loader must import `agent.py` and discover a documented symbol such as:

```python
def create_agent() -> PokerAgent:
    ...
```

Prefer this factory function over requiring a specific class name.

---

# Submission validation

Provide:

```bash
arena test path/to/submission
```

It should verify:

```text
✓ submission imports
✓ create_agent exists
✓ agent initializes
✓ no forbidden interface access
✓ legal actions are returned
✓ observation is not mutated
✓ action deadline is respected
✓ agent survives repeated hands
✓ deterministic mode works when required
```

Also provide:

```bash
arena play submission_a submission_b --game kuhn
```

and:

```bash
arena tournament submissions/ --game kuhn
```

---

# CLI

Use a CLI library only if needed.
`argparse` is sufficient initially.

Target commands:

```bash
arena test ./submissions/team_a

arena play \
  ./submissions/team_a \
  ./submissions/team_b \
  --game kuhn \
  --hands 10000 \
  --seed 42

arena tournament \
  ./submissions \
  --game kuhn \
  --hands 10000

arena replay ./data/replays/hand_123.json

arena benchmark ./submissions/team_a
```

Later:

```bash
arena tournament \
  ./submissions \
  --game holdem \
  --players-per-table 6 \
  --hands 100000
```

---

# Agent isolation

## Development

Initially run agents in-process for simplicity.

This gives:

- easy debugging
- stack traces
- fast iteration

## Intermediate

Move agents to subprocesses.

Use a simple newline-delimited JSON protocol.

Referee sends:

```json
{"type":"act","observation":{...},"legal_actions":[...]}
```

Agent responds:

```json
{"type":"action","action":{"type":"call"}}
```

One JSON object per line.

Do not use pickle across the trust boundary.

## Final tournament

Support Docker.

Recommended restrictions:

- network disabled
- CPU limit
- memory limit
- process limit
- read-only root filesystem where practical
- writable temporary directory only
- no host mounts except required submission/model data
- hard action timeout

Never rely on Docker alone as the only correctness/security mechanism.

---

# RL adapter

The student-facing API should not be redesigned around RL.

Instead create an adapter.

Concept:

```text
Observation
    ↓
encode_observation()
    ↓
NumPy/PyTorch vector

Legal actions
    ↓
action_mask()
    ↓
boolean mask

integer action
    ↓
decode_action()
    ↓
Poker Action
```

Example:

```python
encoded = encoder.encode(observation)

mask = encoder.action_mask(
    observation,
    legal_actions,
)

action_id = policy(encoded, mask)

action = encoder.decode_action(
    action_id,
    legal_actions,
)
```

For restricted Hold'em, prefer a fixed discrete action space.

Possible mapping:

```text
0 fold
1 check/call
2 raise half pot
3 raise pot
4 all in
```

Do not force arbitrary continuous bet sizing into the first RL assignment.

---

# Self-play

Provide infrastructure that lets an agent train against:

- itself
- a fixed baseline
- a pool of historical agents
- randomly sampled opponents

Do not automatically equate "self-play" with "best learning method."

Course assignments should make students compare strategies.

Useful opponent pool:

```text
RandomAgent
CallingStation
AlwaysRaiseAgent
RuleBasedAgent
PreviousCheckpointAgent
CurrentSelfAgent
```

---

# Historical agents

Preserve each team's earlier agents.

Recommended course convention:

```text
teams/
└── team_rocket/
    ├── a01_if_else/
    ├── a03_probability/
    ├── a05_search/
    ├── a08_cfr/
    ├── a10_rl/
    └── final/
```

This enables longitudinal tournaments.

A later assignment may explicitly require new agents to play against the team's own earlier submissions.

---

# Baseline agents

Include deliberately understandable baselines.

At minimum:

```text
RandomAgent
AlwaysFoldAgent
CallingStationAgent
AggressiveAgent
SimpleRulesAgent
```

For Kuhn:

```text
RandomKuhnAgent
SimpleKuhnRulesAgent
```

Avoid shipping an unbeatable or fully optimal baseline before students have completed the corresponding material.

For instructor testing, an optimal/reference implementation may live outside the student-facing examples.

---

# OpenSpiel usage

OpenSpiel is primarily a research/reference dependency.

Use it for:

- Kuhn reference environment
- Leduc reference environment
- CFR
- CFR+
- exploitability calculations
- best response
- equilibrium examples
- validating toy-game behavior

Avoid making students directly depend on the OpenSpiel API for basic assignments.

Wrap OpenSpiel behind course-owned interfaces.

The course API should remain stable if OpenSpiel changes.

---

# PokerKit usage

PokerKit should serve as the default authoritative Hold'em engine.

Wrap it.

Do not expose PokerKit state objects to students.

The `PokerKitAdapter` is responsible for translating:

```text
PokerKit state
    ↓
course Observation

course Action
    ↓
PokerKit operation
```

Adapter tests must cover:

- fold
- check
- call
- raise
- all-in
- side pots
- ties
- split pots
- blind posting
- street transitions
- showdown
- stack accounting

---

# Testing priorities

Tests are essential because poker engines fail in subtle ways.

## Highest-priority invariants

After every hand:

```python
sum(final_stacks) == sum(initial_stacks)
```

unless the game intentionally models rake.

Also verify:

```text
no negative stacks
no card appears twice
no action occurs out of turn
no player bets chips they do not possess
all pots are fully distributed
folded players cannot win at showdown
hidden information remains hidden
same seed + same policies => same result
```

Use property-based testing later if useful.

---

# Logging

Use Python's `logging` module.

Avoid print statements in library code.

Student stdout/stderr must not corrupt referee communications.

For subprocess agents:

- protocol on stdin/stdout
- diagnostic logs on stderr

Persist important events.

Recommended event types:

```text
MATCH_STARTED
HAND_STARTED
CARDS_DEALT
ACTION_REQUESTED
ACTION_RECEIVED
ACTION_TIMEOUT
INVALID_ACTION
STREET_ADVANCED
SHOWDOWN
HAND_FINISHED
MATCH_FINISHED
AGENT_CRASH
```

---

# Tournament database

SQLite is sufficient.

Suggested tables:

```text
agents
tournaments
matches
hands
actions
standings
faults
```

Store large replay/event streams as files if that is simpler, while retaining file paths and summary metadata in SQLite.

Do not prematurely optimize.

---

# Reproducibility

Every graded run must record:

- code version / git commit of arena
- submission identity/version
- Python version
- dependency lock
- game configuration
- tournament configuration
- RNG seed(s)
- timeout settings

Tournament output should be reproducible where possible.

---

# Academic integrity considerations

Students must not be able to inspect:

- opponent source code during tournament execution
- hidden engine state
- future RNG output
- private cards
- filesystem contents belonging to other submissions

Tournament containers should not share writable volumes.

Network access should be disabled unless an assignment explicitly requires it.

Do not create anti-cheating systems that interfere with normal student debugging.

Prefer clear boundaries and auditability.

---

# Instructor tooling

Provide easy ways to inspect agents.

Useful commands/features:

```text
show action frequencies
show bankroll over time
show results by seat
show results by opponent
show timeout/error counts
replay selected hand
replay biggest win/loss
export tournament CSV
```

For Kuhn/Leduc, later add:

```text
estimated policy by information state
exploitability
best-response value
```

These features are pedagogically more valuable than a flashy frontend.

---

# Human-vs-agent GUI

The arena must include a lightweight GUI that allows a student to play directly against an agent.

This is a teaching/debugging tool, not part of the authoritative game engine.

The GUI must use the same referee and observation interfaces as automated matches.

Do not create a second implementation of poker rules inside the GUI.

Architecture:

```text
                 ┌─────────────────────┐
                 │      GUI View       │
                 │ cards / pot / bets  │
                 │ buttons / history   │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │   GUI Controller    │
                 └──────────┬──────────┘
                            │
                  human action / update
                            │
                            ▼
                 ┌─────────────────────┐
                 │      Referee        │
                 │ authoritative state │
                 └───────┬───────┬─────┘
                         │       │
                  Observation   Observation
                         │       │
                  ┌──────▼──┐  ┌─▼──────────┐
                  │ Human   │  │ Student Bot │
                  │ Agent   │  │             │
                  └─────────┘  └─────────────┘
```

The human player should be represented through the same conceptual agent boundary as a bot.

Provide a `HumanAgent` adapter whose `act()` waits for a GUI-selected legal action.

The referee must remain unaware of whether a seat is controlled by:

- a human
- an in-process bot
- a subprocess bot
- a Dockerized bot

---

# GUI technology

Prefer a local browser-based GUI.

Recommended default:

- FastAPI or Starlette for a very small local application
- server-rendered HTML or a minimal static HTML/JavaScript frontend
- WebSocket or simple polling only if genuinely needed
- no React build toolchain unless the project later justifies it

A simpler implementation using Flask is acceptable.

Avoid requiring students to install Node.js merely to use the course GUI.

The GUI should launch locally with a command such as:

```bash
arena gui
```

or:

```bash
arena play-human ./submissions/team_a --game kuhn
```

Preferred behavior:

```bash
uv run arena play-human \
  ./submissions/team_a \
  --game kuhn \
  --seed 42
```

opens or prints a local URL such as:

```text
http://127.0.0.1:8000
```

Do not expose the GUI to external network interfaces by default.

Bind to localhost unless explicitly configured otherwise.

---

# GUI game modes

The GUI should eventually support:

```text
Human vs RandomAgent
Human vs selected student submission
Human vs instructor baseline
Human + bots at a Hold'em table
Spectator replay mode
```

Initial implementation only needs:

```text
Human vs one bot in Kuhn poker
```

Later stages may add:

```text
Human vs one bot in Leduc
Human vs bots in Hold'em
Replay viewer
```

---

# GUI information security

The GUI must obey the same hidden-information firewall as a student agent.

During a live hand, the human-facing GUI may display only information legally visible to the human player.

Do not expose:

- opponent hole cards
- deck order
- future board cards
- burn cards
- RNG state
- authoritative internal state
- hidden engine debugging values

After a hand is complete, the GUI may optionally reveal opponent cards when they would normally be shown at showdown or when instructor/debug mode explicitly permits complete replay visibility.

Never generate the GUI directly from an authoritative engine object's `repr()` or serialized state.

Always render from a dedicated human-visible view model derived from `Observation` plus explicitly public hand metadata.

---

# GUI visual requirements

Keep the interface simple and instructional.

At minimum display:

- game name
- hand number
- player's private cards
- public board cards
- pot
- player's stack
- opponent stack(s)
- dealer/button indicator where relevant
- current amount to call
- action history
- legal action controls
- hand result after completion
- next hand / restart control

For Hold'em later, display:

- all seats around a table or in a clearly readable list
- stack size for each player
- current bet for each active player
- folded/all-in state
- button
- small blind
- big blind
- board
- pot
- side pots if useful
- action log

The GUI should emphasize readability over casino-style visual effects.

Do not spend substantial implementation effort on animations.

---

# GUI action controls

Only legal actions may be clickable.

For Kuhn/Leduc, buttons may simply be:

```text
Check
Bet
Call
Fold
Raise
```

For restricted Hold'em:

```text
Fold
Check/Call
Raise 1/2 Pot
Raise Pot
All In
```

For unrestricted no-limit Hold'em:

- show fold/check/call controls as applicable
- provide a numeric raise input or slider
- enforce `min_raise_to <= amount <= max_raise_to`
- validate server-side as well as client-side

The authoritative referee must validate the action even if the GUI already validated it.

Never trust browser-side validation.

---

# HumanAgent

Implement a human-controlled agent abstraction.

Conceptually:

```python
class HumanAgent(PokerAgent):
    def __init__(self, action_provider: HumanActionProvider):
        self.action_provider = action_provider

    def act(self, observation, legal_actions):
        return self.action_provider.wait_for_action(
            observation,
            legal_actions,
        )
```

Do not literally block the main web server event loop if using an asynchronous server.

The controller may instead pause the match state until the human submits an action.

The important architectural rule is that the human seat participates through the same public observation/action contract.

---

# GUI controller

Keep GUI state management separate from game logic.

The controller is responsible for:

- creating the match
- assigning seats
- advancing bot turns automatically
- pausing when a human action is required
- exposing a sanitized current view
- accepting a human action
- asking the referee to validate/apply it
- continuing until the next human decision or hand end
- starting the next hand
- loading replay data

The controller must not implement:

- betting rules
- hand ranking
- pot settlement
- legal-action computation
- card dealing

Those belong to the referee/game engine.

---

# GUI view models

Create explicit view models instead of passing engine models into templates.

Example:

```python
@dataclass(frozen=True)
class TableView:
    game: str
    hand_id: str
    hero_seat: int

    private_cards: tuple[str, ...]
    board_cards: tuple[str, ...]

    pot: int
    amount_to_call: int

    players: tuple["PlayerView", ...]
    actions: tuple["ActionView", ...]
    legal_actions: tuple["ActionView", ...]

    hand_complete: bool
    result_message: str | None
```

A `TableView` must contain only information safe for the human player to see.

Tests should verify this.

---

# Playing against a selected submission

Support a command like:

```bash
arena play-human ./submissions/team_rocket --game kuhn
```

The submission must be loaded through the same normal submission loader used by automated matches.

Do not create a separate relaxed loading path for GUI play.

This ensures:

```text
if the agent works in the GUI,
it should work in the tournament
```

and vice versa.

For final-stage isolated agents, the GUI should also be able to play against subprocess/container-backed agents using the same `AgentHandle` abstraction as tournament execution.

---

# Agent debugging mode

The GUI may offer an optional debugging panel for the student's own agent.

This mode may show:

- agent execution time
- action returned
- legal action list
- public observation supplied to the agent
- student's optional debug message
- timeout/error information

It must NOT reveal hidden game state.

If agents are allowed to emit explanations, use a dedicated optional field/channel such as:

```python
AgentDecision(
    action=Call(),
    debug="Estimated villain bluff frequency: 0.31",
)
```

Do not require explanatory output for tournament compatibility.

Ignore debug messages during scored tournaments unless explicitly logged for development.

---

# Replay GUI

Design the GUI so it can later render saved replay files.

Replay controls may include:

```text
Previous action
Next action
Start
End
Autoplay
Pause
```

For instructor/debug replay mode, optionally support:

```text
Reveal all cards
```

For student-visible replay mode, hidden cards must remain hidden unless they were legally revealed.

The replay viewer should read replay logs.

It must not reimplement game logic merely to reconstruct the visual state.

---

# GUI testing

Add tests for:

```text
GUI launches
human seat receives only sanitized observations
illegal actions are rejected
legal actions advance the game
bot turns advance automatically
hand completion is displayed
same seed produces same hand
GUI and CLI referee produce equivalent outcomes
opponent hidden cards never appear in live human view
```

Where possible, test the controller independently of the browser layer.

The browser layer should remain thin.

---

# GUI development priority

The GUI is useful early because students can directly experience their agent's behavior.

Add the first Kuhn GUI after the core Kuhn referee and match runner are working.

Revised early development order:

```text
1. Public API
2. Native Kuhn referee
3. Automated Kuhn matches
4. Kuhn replay logging
5. Human-vs-agent Kuhn GUI
6. Kuhn tournament runner
7. OpenSpiel/reference tooling
8. Leduc
9. Hold'em
```

Do not delay the first classroom release for a polished GUI.

A plain but functional interface is sufficient.

---

# Visualization

Do not make visualization a prerequisite for core functionality.

A replay viewer is useful later.

Start with terminal output.

Potential later web UI:

```text
Leaderboard
Table view
Current hand
Action history
Stack sizes
Hole cards after showdown
Board
Tournament standings
Agent statistics
```

Keep authoritative game logic entirely outside the UI.

---

# Coding standards

Use:

```text
src/ layout
type hints
small modules
immutable public models where practical
explicit dependency injection for RNG
pytest
ruff
```

Prefer:

```python
def legal_actions(state: GameState, seat: int) -> tuple[Action, ...]:
    ...
```

over deeply stateful global objects when practical.

Avoid:

- global mutable state
- hidden singleton RNGs
- monkey patching
- reflection-heavy plugin systems
- metaclass magic
- unnecessary inheritance
- dynamic imports scattered through the codebase

Keep agent loading isolated in one subsystem.

---

# Error handling

Student errors are expected.

The arena should distinguish:

```text
ArenaBug
EngineError
InvalidAgentAction
AgentTimeout
AgentCrash
SubmissionLoadError
ProtocolError
```

A single bad student agent should not bring down a full tournament.

Instructor-facing logs should preserve stack traces.

Student-facing errors should be concise and actionable.

---

# Performance

Kuhn and Leduc tournaments should support very large hand counts quickly.

Do not optimize Hold'em prematurely.

First priorities:

1. correctness
2. reproducibility
3. isolation
4. clear debugging
5. speed

Only optimize after profiling.

Avoid creating one Docker container per hand.

Persistent agent processes/containers are preferred for tournament play.

---

# Assignment progression supported by the infrastructure

The environment should comfortably support something like:

## Assignment 1
Kuhn poker using hard-coded `if` statements.

## Assignment 2
Utility and stochastic policies.

## Assignment 3
Probability / opponent models.

## Assignment 4
Game trees and imperfect-information reasoning.

## Assignment 5
Leduc poker.

## Assignment 6
Monte Carlo methods.

## Assignment 7
CFR / regret minimization.

## Assignment 8
Tabular reinforcement learning on toy poker.

## Assignment 9
Restricted Hold'em.

## Assignment 10
Function approximation / neural agents.

## Final project
Six-player no-limit Texas Hold'em tournament.

Do not bake assignment numbering into the library.

---

# Initial implementation milestones

Agents working on this repository should implement in this order.

## Milestone 1 — Repository bootstrap

Create:

- `pyproject.toml`
- package skeleton
- pytest configuration
- ruff configuration
- CLI entry point
- public `PokerAgent`
- public action models
- public observation models

Add a smoke test.

## Milestone 2 — Native Kuhn referee

Implement a minimal course-owned Kuhn poker engine first.

Why:

- tiny state space
- easy to audit
- no major dependency required
- ideal testbed for the public API

Support:

- two players
- deterministic seed
- legal actions
- observation generation
- complete hand logging

Add `RandomAgent`.

## Milestone 3 — Kuhn match runner and replay

Support:

```bash
arena play
```

Add:

- repeated hands
- seat swapping
- bankroll accounting
- JSON replay logs

## Milestone 4 — Human-vs-agent Kuhn GUI

Add:

```bash
arena play-human ./baselines/kuhn_rules_agent --game kuhn
```

Requirements:

- local browser GUI
- human receives only legal/public information
- buttons expose only legal actions
- bot turns advance automatically
- completed hands can be restarted
- same referee used by CLI matches
- same submission loader used by tournament play
- deterministic seed support
- GUI controller tests

## Milestone 5 — Kuhn tournament runner

Support:

```bash
arena tournament
```

Add:

- round robin
- repeated hands
- seat swapping
- bankroll accounting
- CSV/console results

## Milestone 6 — OpenSpiel validation

Add OpenSpiel as an optional/reference dependency.

Cross-check native Kuhn behavior where practical.

Add instructor-only CFR/exploitability examples.

## Milestone 7 — Leduc

Wrap or implement Leduc behind the same API.

Do not modify student-facing API unless unavoidable.

## Milestone 8 — PokerKit Hold'em adapter

Add PokerKit.

Build restricted Hold'em first.

Test all critical chip/pot/action invariants.

## Milestone 9 — RL encoding layer

Add:

- fixed observation encoding
- discrete actions
- action masking
- simple Q-learning example

Only after the ordinary agent API is stable.

## Milestone 10 — Subprocess execution

Introduce JSONL protocol.

Add hard deadlines.

Ensure crashes/timeouts do not kill the arena.

## Milestone 11 — Docker execution

Add final tournament isolation.

## Milestone 12 — Full-table tournament

Support:

- 6 players
- table balancing
- seat rotation
- many scoring hands
- standings
- complete logs
- final-table mode

---

# Definition of done for the initial environment

The first usable classroom release is complete when all of the following work:

```bash
uv sync
uv run pytest
```

and:

```bash
uv run arena test ./baselines/random_agent
```

and:

```bash
uv run arena play \
  ./baselines/random_agent \
  ./baselines/kuhn_rules_agent \
  --game kuhn \
  --hands 1000 \
  --seed 42
```

and:

```bash
uv run arena play-human \
  ./baselines/kuhn_rules_agent \
  --game kuhn \
  --seed 42
```

which launches a local GUI where a human can complete a legal Kuhn hand against the selected agent without seeing hidden information.

and:

```bash
uv run arena tournament \
  ./baselines \
  --game kuhn \
  --hands 10000 \
  --seed 42
```

The same tournament run with the same code, configuration, and seed must produce the same results.

A replay from that tournament must be inspectable and sufficient to reconstruct every authoritative action.

---

# Guidance for AI coding agents

When implementing this repository:

1. Read this file before changing architecture.
2. Preserve the public student-facing API unless explicitly instructed otherwise.
3. Favor small working increments over speculative infrastructure.
4. Add tests with every new game-rule behavior.
5. Never expose authoritative state to student agents.
6. Never silently coerce an illegal student action without logging it.
7. Keep deterministic execution possible.
8. Do not add heavyweight dependencies without justification.
9. Do not rewrite working components merely to introduce a pattern.
10. When a choice affects classroom ergonomics, favor the option that is easiest for students to understand and debug.
11. When a choice affects tournament correctness, favor the option that is easiest for the instructor to audit and reproduce.
12. Keep poker-engine dependencies behind adapters.
13. Maintain compatibility between simple rule-based agents and later learned agents.
14. Treat replayability, timeouts, and hidden-information boundaries as core features, not polish.
15. Never assume that a neural or RL implementation is inherently superior to a rule-based one.

---

# Near-term task for the coding agent

If this repository is currently empty, begin by implementing Milestones 1–5 only:

1. Bootstrap the Python project with `uv`.
2. Create the public API.
3. Implement two-player Kuhn poker locally.
4. Implement `RandomAgent`.
5. Implement a simple non-optimal rule-based Kuhn agent.
6. Add deterministic hand execution.
7. Add replay logging.
8. Add head-to-head match execution.
9. Add a minimal human-vs-agent Kuhn GUI.
10. Ensure the GUI uses the same referee and observation API as automated matches.
11. Add a round-robin tournament.
12. Add CLI commands for `test`, `play`, `play-human`, and `tournament`.
13. Add comprehensive tests, including hidden-information tests for the GUI.

Do not implement Leduc, PokerKit, OpenSpiel, RL, subprocesses, Docker, or a polished frontend until the Kuhn arena and basic human-vs-agent GUI are correct, deterministic, and well tested.

# estimator

A Claude Code skill that estimates the cost — in tokens, dollars, and human
review time — of building a software project with AI coding agents, based on
ACEM (Agentic Cost Estimation Model), a 2026 cost-estimation framework for
agentic software engineering. The repo includes the source paper, the skill
implementation, and a written critique of the model's assumptions and gaps.

## Highlights

- **Retrospective and prospective estimation** — size an already-built
  codebase (count its functions, classes, tests, docs) or a planned project
  (from Use Case/Story/Function Points), and get a token + human-review cost
  forecast either way.
- **Monte Carlo cost ranges, not false-precision point estimates** — model
  uncertain inputs (rejection rate, retries, context growth) as distributions
  and get back p10/p50/p90 cost bands.
- **Non-stationary and parallel-pipeline aware** — rejection rates can drift
  over a project, context growth can be linear/sublinear/capped, and
  multi-track (parallel agent) pipelines report per-track subtotals.
- **Calibration confidence tracking** — every cost figure carries a
  `cold-start` / `partial` / `calibrated` label plus staleness warnings, so a
  guess never looks as trustworthy as a number backed by real pilot data.
- **Documented weaknesses** — `docs/ACEM_WEAKNESSES.md` is a critical read of
  the model's own assumptions, what's missing, what will drift as models and
  vendors change, and what would improve it.

## Getting Started

### Prerequisites

- [Claude Code](https://claude.com/claude-code)
- Python 3.9+ (for the calculator script; standard library only, no
  dependencies to install)

### Installation

Clone the repo and symlink (or copy) the skill into Claude Code's personal
skills directory so it's discoverable by the `Skill` tool:

```bash
git clone https://github.com/keithmackay/estimator.git
cd estimator
ln -s "$(pwd)/skill/acem-cost-estimation" ~/.claude/skills/acem-cost-estimation
```

## Usage

Inside a Claude Code session, ask it to estimate agentic build cost for a
codebase or planned project — the `acem-cost-estimation` skill activates
automatically:

> "What would it have cost an AI agent to build this codebase?"

Or run the calculator directly against a JSON task breakdown:

```bash
python3 skill/acem-cost-estimation/acem_calculate.py \
  skill/acem-cost-estimation/references/example_input.json
```

For a cost range instead of a single figure, run a Monte Carlo simulation
over inputs expressed as `{"low": a, "mode": m, "high": b}` distributions:

```bash
python3 skill/acem-cost-estimation/acem_calculate.py \
  skill/acem-cost-estimation/references/example_input_advanced.json \
  --montecarlo 3000 --seed 42
```

To flag calibration constants that are stale, underpowered, or tied to a
superseded agent version:

```bash
python3 skill/acem-cost-estimation/acem_calculate.py \
  skill/acem-cost-estimation/references/example_input_advanced.json \
  --calibration-log skill/acem-cost-estimation/references/calibration_log_example.json
```

See `skill/acem-cost-estimation/SKILL.md` for the full input schema and
workflow, and `skill/acem-cost-estimation/references/acem-paper-summary.md`
for a condensed reference of the underlying formulas.

## Architecture

| Path | Contents |
|---|---|
| `docs/2608.02582v1.pdf` | The source paper: "ACEM: A Cost Estimation Model for Agentic Software Engineering" (El-Ramly, 2026) |
| `docs/ACEM_WEAKNESSES.md` | Critique of the model's assumptions, gaps, and what would improve it |
| `skill/acem-cost-estimation/SKILL.md` | The skill's workflow: how to inventory a codebase and map it to ACEM's cost formulas |
| `skill/acem-cost-estimation/acem_calculate.py` | Calculator implementing ACEM's formulas, plus Monte Carlo, non-stationary parameters, parallel pipelines, and calibration tracking |
| `skill/acem-cost-estimation/references/` | Formula reference and worked example inputs |

## Development

There's no build step or test suite yet — the calculator is a single
dependency-free Python script. To sanity-check changes:

```bash
python3 skill/acem-cost-estimation/acem_calculate.py \
  skill/acem-cost-estimation/references/example_input.json
```

Compare the output against `docs/2608.02582v1.pdf` Tables 5–6 for the
model's own worked examples.

## Contributing

This started as a personal exploration of the ACEM paper; issues and PRs
that improve the calculator, extend the skill's codebase-inventory heuristics,
or add real calibration data are welcome.

## License

[MIT](LICENSE)

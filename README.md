# estimator

A Claude Code skill that estimates the cost — in tokens, dollars, and human
review time — of building a software project with AI coding agents, based on
[ACEM (Agentic Cost Estimation Model)](https://arxiv.org/abs/2608.02582)
(El-Ramly, "ACEM: A Cost Estimation Model for Agentic Software Engineering,"
arXiv:2608.02582, 2026), a cost-estimation framework for agentic software
engineering. The repo includes the source paper, the skill implementation,
and a written analysis of opportunities to strengthen the model.

> [!WARNING]
> ACEM is an early-stage, unvalidated research proposal — its own authors
> state it "has not yet been validated against real project data." This
> repo's calculator and skill are exploratory tooling for testing the model,
> not a production cost-estimation tool. Every constant, default, and
> heuristic here is a placeholder pending real calibration data (see
> `docs/ACEM_OPPORTUNITIES.md`). **Do not treat any dollar figure this tool
> produces as an accurate or guaranteed estimate of real-world agentic
> development cost.**

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
- **Documented improvement opportunities** — `docs/ACEM_OPPORTUNITIES.md`
  examines the model's own assumptions, what's missing, what will drift as
  models and vendors change, and what would strengthen it.

## Getting Started

### Prerequisites

- A supported coding agent: [Claude Code](https://claude.com/claude-code),
  [Codex](https://developers.openai.com/codex), [Antigravity](https://antigravity.google/),
  or [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- Python 3.9+ (for the calculator script; standard library only, no
  dependencies to install)

### Installation

The skill lives at `skill/acem-cost-estimation/` and works natively on all
four platforms — clone the repo first:

```bash
git clone https://github.com/keithmackay/estimator.git
cd estimator
```

**Claude Code** — symlink (or copy) into the personal skills directory:
```bash
ln -s "$(pwd)/skill/acem-cost-estimation" ~/.claude/skills/acem-cost-estimation
```
Then invoke with `/acem-cost-estimation` or just ask a qualifying question —
the skill activates automatically.

**Codex** — add an entry to your plugin marketplace
(`~/.agents/plugins/marketplace.json`):
```json
{
  "name": "personal",
  "interface": { "displayName": "Personal Plugins" },
  "plugins": [
    {
      "name": "acem-cost-estimation",
      "source": { "source": "local", "path": "/absolute/path/to/estimator/skill/acem-cost-estimation/" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
```

**Antigravity** — copy into the global or workspace skills directory:
```bash
cp -r skill/acem-cost-estimation ~/.gemini/antigravity/skills/acem-cost-estimation   # global
cp -r skill/acem-cost-estimation .agents/skills/acem-cost-estimation                 # workspace-only
```

**Gemini CLI** — install the extension directly from this repo:
```bash
gemini extensions install https://github.com/keithmackay/estimator
```
(Gemini CLI extensions install from a repo root; if that doesn't pick up the
skill automatically, clone the repo and point Gemini CLI at the
`skill/acem-cost-estimation/` subdirectory instead.)

Full per-platform detail, a compatibility matrix, and platform doc links live
in `skill/acem-cost-estimation/README.md`.

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
| `docs/ACEM_OPPORTUNITIES.md` | Analysis of the model's assumptions, gaps, and opportunities to strengthen it |
| `skill/acem-cost-estimation/SKILL.md` | The skill's workflow (Claude Code / Antigravity native format): how to inventory a codebase and map it to ACEM's cost formulas |
| `skill/acem-cost-estimation/acem_calculate.py` | Calculator implementing ACEM's formulas, plus Monte Carlo, non-stationary parameters, parallel pipelines, and calibration tracking |
| `skill/acem-cost-estimation/references/` | Formula reference and worked example inputs |
| `skill/acem-cost-estimation/.codex-plugin/`, `skills/` | Codex plugin manifest and skill copy |
| `skill/acem-cost-estimation/gemini-extension.json`, `GEMINI.md` | Gemini CLI extension manifest and context-file include |
| `skill/acem-cost-estimation/README.md` | Per-platform install instructions and compatibility matrix for the skill itself |

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

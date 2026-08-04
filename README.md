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

## ACEM Estimator and Extensions

All credit for ACEM itself — the cost model, its constructs (Revision
Factor, Context Factor, HITL Intensity Score), and the sizing-metric
mappings — belongs to **Mohammad El-Ramly** (Faculty of Computers and
Artificial Intelligence, Cairo University), in
["ACEM: A Cost Estimation Model for Agentic Software Engineering"](https://arxiv.org/abs/2608.02582)
(arXiv:2608.02582, 2026). This repo is a third-party implementation and
extension of that paper, not affiliated with the original author. The paper
itself proposes ACEM as a first-draft structure and explicitly invites the
community to calibrate, test, and extend it (Section 5) — this project is
one attempt to take that invitation up. `docs/ACEM_OPPORTUNITIES.md` is our
close reading of the paper's own stated limitations and future-work section,
and the extensions below map directly onto opportunities it identifies.

What this repo adds on top of the original model, and why:

- **Monte Carlo cost distributions** (`--montecarlo`). The paper flags, in
  its discussion of non-determinism (Section 4.3), that "the appropriate
  output of an agentic cost model may be a probability distribution over
  costs, not a single figure," and names Monte Carlo simulation as a
  high-priority future direction. We implemented that directly: any of
  `rejection_rate`, `retries_per_rejection`, or `alpha` can be given as a
  `{low, mode, high}` distribution, returning p10/p50/p90 cost bands instead
  of a point estimate.
- **Non-stationary rejection rates and alternative context-growth curves**
  (`context_model: linear | sublinear | capped`). The paper names both of
  these as simplifying assumptions it makes for tractability (Assumption A3
  and the discussion after Equation 7), noting real agents may improve or
  degrade over a project and that context growth may not be linear for
  agents using compression or summarization. We made both swappable inputs
  rather than fixed assumptions.
- **An LLM-perceived complexity axis** (`llm_complexity_score()`). The paper
  cites its own supporting evidence (Bai et al.; Xie et al.) that
  human-judged task complexity correlates weakly with actual token
  consumption, and names a second "LLM-perceived complexity" dimension
  without fully operationalizing it (Section 3.2.2). We added a scorer so
  the human-judged Simple/Medium/Complex tier can be checked against a
  model-facing signal rather than trusted alone.
- **Parallel-pipeline / per-track support** (`track` field). ACEM's Context
  Factor assumes a single sequential pipeline (Assumption A1), which the
  paper names as a scope boundary and an explicit direction for future work.
  Multi-agent fan-out is increasingly the default architecture rather than
  the exception, so we added per-track grouping and subtotals as a practical
  approximation ahead of a fuller concurrent-context model.
- **Calibration confidence and staleness tracking**
  (`--calibration-log`, `confidence` labels). The paper is explicit that
  every constant is symbolic pending calibration and warns that constants
  must be recalibrated whenever the agent or model version changes
  (Assumption A4). Nothing in the original model distinguishes a calibrated
  number from a cold-start guess at the point of use, so we added
  per-constant `sample_size`/`calibrated_date` tracking that flags entries
  that are underpowered, stale, or tied to a superseded agent version.
- **A retrospective (codebase-first) mode.** The paper's worked examples all
  size a *planned* project from sizing metrics. Estimating what an
  *already-built* codebase would have cost to build agentically — this
  skill's primary use case — is a natural but unaddressed extension; we
  built the artifact-inventory workflow needed to run ACEM in that
  direction, and documented it clearly as an extension rather than
  something the original paper claims to support.

Every one of these is exploratory tooling for testing ACEM's ideas, not a
validated improvement — see the warning above and
`docs/ACEM_OPPORTUNITIES.md` for the full analysis, including the one
opportunity we can't implement ourselves: a real, multi-organization
calibration dataset, which the paper itself names as the necessary next step
for the whole model.

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

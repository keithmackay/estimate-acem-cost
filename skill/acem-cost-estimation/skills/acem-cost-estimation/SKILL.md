---
name: acem-cost-estimation
description: Use when the user wants to estimate what it would have cost (time/dollars) for an AI coding agent to build an existing codebase, or wants a token+HITL cost forecast for a planned agentic software project — applies the ACEM (Agentic Cost Estimation Model) methodology.
---

# ACEM Cost Estimation

## Overview

ACEM (El-Ramly, 2026, "ACEM: A Cost Estimation Model for Agentic Software
Engineering") models agentic dev cost as `Total_Cost = C_LLM + C_HITL + C_Infra`:
token consumption cost, human-in-the-loop review/rework cost, and infrastructure
cost. It uses two corrective multipliers — Revision Factor (RF, retry overhead)
and Context Factor (CF, context accumulation) — and a HITL Intensity Score (HIS)
to classify oversight level. Full paper: `references/acem-paper-summary.md`.

**This skill runs ACEM in reverse of its primary design**: the paper sizes a
*planned* project from Use Case/Story/Function Points. Here you're sizing an
*already-built* codebase, so artifact counts come from the repo itself rather
than a sizing estimate. Say so explicitly in the output — this is a legitimate
but unvalidated extension of the model (see `references/opportunities.md`).

> [!WARNING]
> ACEM has not been validated against real project data, and this skill's
> defaults are cold-start placeholders, not calibrated constants. Any cost
> figure this skill produces is for exploratory and testing purposes only —
> state that limitation in every report, and never present a dollar figure
> as a guaranteed or precise estimate.

## When to Use

- "What would it have cost an AI agent to build this codebase?"
- "Estimate agentic dev cost/time for this repo/project."
- Comparing a hypothetical AI-built cost against known human dev cost/timeline.

Not for: estimating human-only dev cost (use COCOMO/Story Points instead — this
model is specifically about agentic/LLM-driven development).

## Procedure

### 1. Inventory the codebase → artifact counts

Use `find`/`grep`/`cloc`/language-aware tooling to count units per ACEM artifact
type (Table 2 rows). Classify each unit's complexity as Simple/Medium/Complex
using human-perceived criteria (single responsibility & no deps = Simple;
multiple responsibilities/moderate ambiguity = Medium; cross-cutting/high
ambiguity = Complex — inspect file size, cyclomatic-ish signals, dependency
fan-out as proxies).

| Artifact type | How to count in a repo |
|---|---|
| Requirements elaboration | 1 per major feature/epic (infer from README/CHANGELOG/issue history, or 1 per top-level module) |
| Use case / user story | 1 per distinct user-facing behavior (routes, CLI commands, API endpoints) |
| Function/method implementation | count of non-trivial functions/methods |
| Class/module implementation | count of classes or files acting as modules |
| Unit test suite | count of test files |
| Integration test scenario | count of integration/e2e test cases |
| Code review | 1 per module (assume every module was reviewed once) |
| Bug diagnosis and fix | estimate from commit history (`git log --grep="fix"`) if available, else omit |
| Documentation | 1 per doc page/section |
| Refactoring | estimate from commit history if available, else omit |

If a repo has no git history, no test directory, or no clear feature
boundaries, don't guess a precise count — use the coarsest artifact type you
can defend (e.g. "class/module implementation" counted from file count
alone), state which rows were skipped and why, and widen the Monte Carlo
range (Step 7) to reflect that extra uncertainty rather than presenting a
falsely narrow estimate.

### 2. Assign BaseTokens per unit

No universal constants exist (β is calibrated per agent/domain — Section 3.6
of the paper). Absent pilot data, use these cold-start defaults, then flag
them clearly as uncalibrated:

| Complexity | Input tokens/unit | Output tokens/unit |
|---|---|---|
| Simple | 6,000–10,000 | 2,000–4,000 |
| Medium | 15,000–30,000 | 4,000–8,000 |
| Complex | 50,000–150,000+ | 10,000–30,000+ |

Rough whole-project fallback if you can't break out per-artifact-type: ~3M
input tokens / ~1M output tokens per "task" as a benchmark-derived average
(paper Section 3.2.2). Prefer the granular table when you can enumerate units.

### 3. Estimate RF (retry overhead)

`RF = 1 + (rejection_rate × retries_per_rejection)`. Without calibration data,
derive rejection_rate from `1 - benchmark_success_rate` for a comparably
capable agent on similar task types (e.g. SWE-bench-style pass rates), and
assume 1.5 retries/rejection as a starting point. Typical range: RF ≈ 1.2
(simple, reliable agent) to RF ≈ 1.8+ (complex, less reliable).

### 4. Estimate CF (context growth)

`CF = 1 + α × (i/N)`, i = task position, N = total tasks in the pipeline. Use
α ≈ 0.3 for short/modular pipelines (context resets between modules), α ≈
0.5–0.8 for long monolithic pipelines with full history carried forward. Use
the *average* i/N (≈0.5–0.65) across all tasks if you're not modeling per-task
position.

### 5. Estimate HITL cost

Classify the project's overall HIS level (Table 4 logic): low-risk, well-tested
domain → HIS-1/2 (1 checkpoint per feature/story); safety-relevant or
regulated → HIS-3/4 (per-task or continuous review). Assume review duration
D_i and rework duration RW_i in hours based on artifact complexity (10 min /
Simple, 30 min / Medium, 1-3 hrs / Complex is a reasonable starting split), and
use a fully-loaded reviewer rate W (ask the user, or default $75/hr).

### 6. Estimate C_Infra

Usually small relative to C_LLM/C_HITL for typical pipelines; either ask the
user for known cloud/CI costs or omit with a note that it's excluded.

### 7. Compute

Build a JSON input (see `references/example_input.json` for the basic schema,
`references/example_input_advanced.json` for every advanced feature below)
and run:

```bash
python3 acem_calculate.py input.json
```

This returns C_LLM, C_HITL, C_Infra, Total_Cost, and each component's %
share — mirroring the paper's Table 5/6 output format, plus a per-track
breakdown and a per-group calibration-confidence label.

**Prefer a distribution over a point estimate** (the model's single biggest
opportunity for improvement — see `references/opportunities.md` §1/§5.2). Give any
of `rejection_rate`, `retries_per_rejection`, or top-level `alpha` as
`{"low": a, "mode": m, "high": b}` instead of a plain number, then run:

```bash
python3 acem_calculate.py input.json --montecarlo 3000 --seed 42
```

This returns p10/p50/mean/p90 for Total_Cost, C_LLM_total, and C_HITL_total
instead of a single figure. **Always report this range to the user, not the
point estimate**, whenever any input is uncertain enough to express as a
distribution — which in practice is almost always true pre-calibration.

**Other advanced input features** (all optional, all backward compatible with
plain numbers):

| Feature | How | Addresses |
|---|---|---|
| Non-stationary rejection rate/retries | `{"start": a, "end": b}` — interpolated linearly across the group's `position_factor` | agents plausibly get better/worse over a project; a constant r_i can't capture that |
| Context growth model | top-level `"context_model": "linear" \| "sublinear" \| "capped"` (+ optional `"context_cap"`) | linear CF overestimates cost for agents with context compression/summarization |
| Parallel pipelines | tag each group with `"track": "backend"` etc. — output reports per-track subtotals | ACEM's sequential-pipeline assumption doesn't fit fan-out/subagent architectures; run each track's `position_factor` relative to *its own* length, and set CF-reset (`position_factor` back near 0) at track boundaries if context isn't shared across tracks |
| LLM-perceived complexity | add `"llm_complexity_score"` (see `llm_complexity_score()`/`llm_complexity_tier()` helpers in the script) | human-judged Simple/Medium/Complex correlates weakly with actual token cost (paper's own cited evidence) — use this as a check on, not a replacement for, the human-judged tier |
| Calibration confidence/staleness | add `"sample_size"` and `"calibrated_date"` (YYYY-MM-DD) per group, or maintain a calibration log (`references/calibration_log_example.json`) and pass `--calibration-log path.json` | tells the reader whether a number is calibrated, a small pilot, or a cold-start guess, and flags constants overdue for recalibration or calibrated against a now-superseded agent version |

### 8. Report

Never present a single dollar figure as if it were precise. Lead with the
Monte Carlo p10/p50/p90 range when inputs are uncertain (the normal case).
State every assumed constant explicitly, and surface each group's
`confidence` label and any `--calibration-log` warnings so the reader can
tell a calibrated number from a cold-start guess. Include: total cost range,
C_LLM vs C_HITL split, per-track subtotals if the pipeline is parallel, which
inputs the estimate is most sensitive to (usually rejection rate and RF), and
what pilot data would sharpen it.

## Common Mistakes

- Reporting a single dollar figure with false precision — ACEM's own authors
  call it "not yet validated against real project data." Always range it.
- Applying CF to token counts that already include accumulated context (double
  counts context growth — see paper Section 3.2.4).
- Forgetting C_Infra even as a placeholder note.
- Treating BaseTokens defaults above as calibrated — they're order-of-magnitude
  placeholders pending real pilot data (Section 3.6/4.4 of the paper).

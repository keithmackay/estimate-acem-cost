---
name: estimate-acem-cost
description: Use when the user wants to estimate what it would have cost (time/dollars) for an AI coding agent to build an existing codebase, or wants a token+HITL cost forecast for a planned agentic software project — applies the ACEM (Agentic Cost Estimation Model) methodology.
---

# ACEM Cost Estimation

## Overview

ACEM (El-Ramly, 2026, "ACEM: A Cost Estimation Model for Agentic Software
Engineering") models agentic dev cost as `Total_Cost = C_LLM + C_HITL + C_Infra`:
token consumption cost, human-in-the-loop review/rework cost, and infrastructure
cost. It uses two corrective multipliers — Revision Factor (RF, retry overhead)
and Context Factor (CF, context accumulation) — and a HITL Intensity Score (HIS)
to classify oversight level. Condensed formula reference:
`references/acem-paper-summary.md` (the full paper is
[arXiv:2608.02582](https://arxiv.org/abs/2608.02582); its PDF isn't bundled
with this skill, so it's not reachable from a standalone Codex/Antigravity/
Gemini CLI install — only the summary is).

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

## Flags

### `--help`

If the user invokes this skill with a `--help` flag (e.g. `/estimate-acem-cost --help`), do not run the procedure. Instead, read and display the contents of `help.md` (in this skill's folder) verbatim, then stop.

### `--version`

If the user invokes this skill with a `--version` flag (e.g. `/estimate-acem-cost --version`), do not run the procedure. Instead:

1. Read the installed version from this skill's own manifest: `.claude-plugin/plugin.json` if present, else `.codex-plugin/plugin.json`, else `gemini-extension.json` — whichever exists for this platform install. If none exist (a bare Claude Code skill with only SKILL.md), read the topmost version heading in `CHANGELOG.md` instead.
2. Print: `estimate-acem-cost v<installed-version>`
3. Best-effort update check — determine this skill's GitHub source repo:
   a. If `.git` exists here and `git remote get-url origin` resolves to a `github.com` URL, use that `owner/repo`.
   b. Otherwise, search this skill's own `README.md` for the first `https://github.com/<owner>/<repo>` URL and use that.
   c. If neither yields a repo, or the `gh` CLI isn't installed/authenticated: stop here. Print nothing further — no status line, no error.
4. If a repo was found: run `gh api repos/<owner>/<repo>/releases/latest -q .tag_name` (strip a leading `v`). Compare to the installed version:
   - Equal → append: `Status: up to date`
   - Installed is older → append: `Status: newer version available (v<latest>). To update: if you installed this via a Claude Code marketplace, run /plugin marketplace update <marketplace-name> then reinstall; otherwise, git pull in your install directory if it's a git checkout, or re-copy from https://github.com/<owner>/<repo> per this README's Installation section.`
   - Installed is newer → append: `Status: ahead of latest release (development checkout)`
   - If the API call fails for any reason (network, auth, rate limit, malformed tag): print nothing further — no status line, no error shown to the user.
5. Stop — do not proceed to run the skill's actual procedure.

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

This is the paper's default linear model; `sublinear`/`capped` alternatives
exist for agents with context compression or summarization — see
`context_model` in Step 7.

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

For per-group/per-track Monte Carlo detail, embedding calibration warnings
in the JSON output, non-stationary parameters, alternative context-growth
curves, parallel pipelines, or an LLM-perceived complexity check, see
`references/advanced-features.md` — situational features, not needed for a
basic estimate.

### 8. Report

Lead with the Monte Carlo p10/p50/p90 range whenever inputs are uncertain
(the normal case) — treat that range as the headline number, not a single
point estimate. Every report should include:

- Total cost range (p10/p50/p90), not a single figure
- C_LLM vs C_HITL split
- Per-track subtotals, if the pipeline is parallel
- Every assumed constant, stated explicitly
- Each group's `confidence` label and any `--calibration-log` warnings, so
  the reader can tell a calibrated number from a cold-start guess
- Which inputs the estimate is most sensitive to (usually rejection rate
  and RF)
- What pilot data would sharpen the estimate

## Common Mistakes

- Reporting a single dollar figure with false precision — ACEM's own authors
  call it "not yet validated against real project data." Always range it.
- Applying CF to token counts that already include accumulated context (double
  counts context growth — see paper Section 3.2.4).
- Forgetting C_Infra even as a placeholder note.
- Treating BaseTokens defaults above as calibrated — they're order-of-magnitude
  placeholders pending real pilot data (Section 3.6/4.4 of the paper).

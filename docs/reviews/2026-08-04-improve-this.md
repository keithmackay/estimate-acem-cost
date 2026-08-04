# improve-this Review — 2026-08-04

**Scope**: Full project (`/Users/Keith.MacKay/Projects/estimator`).

**Project type**: Hybrid — primarily a Claude Code skill / multi-platform
agent-skill collection (SKILL.md + calculator + reference docs, ported to
Codex/Antigravity/Gemini CLI), with a real Python library component
(`acem_calculate.py`) and supporting docs (source paper PDF, opportunities
analysis).

**Categories reviewed**: Token Efficiency & Progressive Disclosure,
Redundancy, Test Coverage & Quality, Clarity & Simplification, Accuracy &
Consistency, Completeness, Code Efficiency. (Security was proposed but
excluded as low-relevance — no network calls or untrusted-input execution.)

This is an evaluation only — no files were modified as part of this review.

## Priority List

```
#1  [Impact: High   | Confidence: High]   Redundancy — full duplicate skill tree (skill/.../skills/.../) with no sync mechanism
#2  [Impact: High   | Confidence: High]   Test Coverage — zero tests exist for the calculator
#3  [Impact: Medium | Confidence: High]   Accuracy & Consistency — "Full paper" link mislabeled; actual PDF not bundled in the portable skill
#4  [Impact: Medium | Confidence: Medium] Accuracy & Consistency — alpha resolved inconsistently between point-estimate and Monte Carlo modes
#5  [Impact: Medium | Confidence: Medium] Redundancy — same "extensions" narrative duplicated across README, opportunities.md, and SKILL.md
#6  [Impact: Medium | Confidence: Medium] Completeness — Monte Carlo output drops per-group/per-track breakdown that point-estimate mode has
#7  [Impact: Medium | Confidence: Medium] Token Efficiency — SKILL.md's advanced-features table is reference material loaded on every invocation
#8  [Impact: Low    | Confidence: Medium] Accuracy & Consistency — SKILL.md's CF step doesn't mention sublinear/capped until later in the doc
#9  [Impact: Low    | Confidence: Medium] Completeness — calibration-log warnings only go to stderr, not into the JSON output
#10 [Impact: Low    | Confidence: Low]    Code Efficiency — alpha re-resolved every group iteration instead of once when it's a plain constant
```

## Categorized Breakdown

### Redundancy

**#1 Duplicate skill tree with no sync mechanism.**
`skill/acem-cost-estimation/skills/acem-cost-estimation/` is a full
byte-copy of `SKILL.md`, `acem_calculate.py`, and all of `references/` —
created for the Codex/Gemini port. There's no build step or symlink keeping
these in sync; today's session already required a manual `rsync` to
reconcile them after edits. Any future edit to the root skill risks silently
drifting from the Codex/Gemini copy (or vice versa) since nothing enforces
or even flags divergence.
Impact: High (silent drift = wrong instructions shipped to some platforms).
Confidence: High (directly observed the sync problem this session).

**#5 The "what we added and why" narrative appears three times.**
The README's "ACEM Estimator and Extensions" section,
`docs/ACEM_OPPORTUNITIES.md` §5, and scattered call-outs in `SKILL.md`
(e.g. the `§1/§5.2` reference) all describe the same six extensions with
overlapping but not identical wording. A reader hits the same information
three times with slightly different framing, and updating one extension's
description means remembering to touch three files.
Impact: Medium (documentation-maintenance burden, not user-facing breakage).
Confidence: Medium (real duplication, but some repetition across
audience-specific docs is arguably intentional).

### Test Coverage & Quality

**#2 No test files exist anywhere in the project.**
`acem_calculate.py` has real branching logic (three context-growth models,
three parameter-spec shapes, Monte Carlo sampling, calibration staleness
checks) with zero automated verification. Every check performed during
development was done manually via ad hoc shell commands rather than a
repeatable suite — regressions would only surface if someone happens to
re-run those same manual checks.
Impact: High (this is a cost-calculation tool; a silent arithmetic bug
directly produces a wrong dollar figure).
Confidence: High.

### Accuracy & Consistency

**#3 "Full paper" link is mislabeled and the actual PDF isn't portable.**
SKILL.md line 15 says "Full paper: `references/acem-paper-summary.md`" —
but that file is a condensed reference, not the full paper; the real PDF
(`docs/2608.02582v1.pdf`) lives outside the skill directory entirely. Anyone
who installs just the skill folder (which is exactly what the README's own
Codex/Antigravity/Gemini instructions do) has no path to the actual source
paper, only a summary mislabeled as the full text.
Impact: Medium (misleads a reader trying to verify the model against the
source).
Confidence: High (directly verified the PDF isn't in the skill tree).

**#4 Alpha resolution differs between point-estimate and Monte Carlo paths.**
In `acem_cost`, alpha is resolved per-group at that group's own
`position_factor` (`_resolve(alpha_spec, pos)` inside the loop). In
`acem_cost_monte_carlo`, alpha is resolved once per sample at a hardcoded
`position_factor=0.5`, regardless of any given group's actual position. If
alpha is ever given as a non-stationary `{start, end}` spec (which
`_resolve`/`_sample` both structurally permit, even though only
rejection_rate/retries are documented as supporting that shape), the two
modes would compute meaningfully different costs for the same input.
Impact: Medium (currently unreachable via documented usage, but the code
doesn't prevent a user from hitting it).
Confidence: Medium (real code-level inconsistency; low likelihood any
current user triggers it since SKILL.md doesn't advertise non-stationary
alpha).

**#8 CF's alternative growth curves are introduced late relative to where
they're used.**
SKILL.md's Step 4 ("Estimate CF") only presents the paper's original linear
formula; the sublinear/capped alternatives aren't mentioned until the
"Other advanced input features" table three steps later. A reader following
the procedure top-to-bottom forms an incomplete mental model of CF before
learning it's configurable.
Impact: Low. Confidence: Medium.

### Completeness

**#6 Monte Carlo mode loses per-group/per-track detail.**
`acem_cost` (point estimate) returns a full breakdown: per-group
RF/CF/tokens/confidence label, plus per-track subtotals.
`acem_cost_monte_carlo` collapses everything to three aggregate
distributions (Total_Cost, C_LLM_total, C_HITL_total) with no group or
track dimension at all — so a user modeling a multi-track pipeline with
uncertain inputs (the exact scenario the advanced example demonstrates)
can't get a distributional answer broken down by track, only in aggregate.
Impact: Medium. Confidence: Medium (real gap, but may be an acceptable,
documented scope choice rather than an oversight — worth confirming
intent).

**#9 Calibration warnings aren't included in the JSON output.**
`--calibration-log` warnings print to stderr as human-readable strings; the
JSON payload on stdout carries no `calibration_warnings` field. Anything
piping the JSON output downstream (e.g., another tool, or a UI) loses this
signal entirely unless it also parses stderr.
Impact: Low. Confidence: Medium.

### Token Efficiency & Progressive Disclosure

**#7 The advanced-features table is reference material loaded on every
invocation.**
SKILL.md's "Other advanced input features" table (non-stationary params,
context models, parallel pipelines, LLM-complexity, calibration log — ~10
lines of dense reference detail) is only relevant when a user actually
wants one of those five specific capabilities, yet it's baked into the
always-loaded SKILL.md alongside the core Steps 1–8 workflow that's needed
on every single estimate. Per the progressive-disclosure principle, this
table is a strong candidate to move into `references/` and be pulled in
only when the situation calls for it, trimming what's loaded on ordinary
invocations.
Impact: Medium. Confidence: Medium (SKILL.md is only 174 lines total, so
the token cost is real but not severe — a judgment call on whether it's
worth the split).

### Code Efficiency

**#10 Alpha is re-resolved on every group iteration even when it's a plain
constant.**
In `acem_cost`, `_resolve(alpha_spec, pos)` runs once per group; when
`alpha_spec` is a plain float (the common case), this repeats identical,
cheap work rather than resolving once before the loop. Negligible at
realistic group-list sizes (tens of groups), but slightly obscures that
alpha is conceptually pipeline-level, not group-level.
Impact: Low. Confidence: Low (real but inconsequential at current scale;
also entangled with the point-estimate/Monte-Carlo inconsistency above, so
fixing one likely touches the other).

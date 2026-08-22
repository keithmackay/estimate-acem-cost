# Advanced Calculator Features

Situational reference for `acem_calculate.py` — only needed when a
particular pipeline calls for one of these, not on every estimate. See
`SKILL.md` for the core Steps 1–8 workflow this extends.

## Monte Carlo detail (`--breakdown`)

`--montecarlo N --breakdown` also returns per-group and per-track
p10/p50/p90 (`groups`, `tracks` in the output), matching the detail level
the point-estimate path already provides. Off by default, since it's more
output than most estimates need — ask the user whether they want this level
of detail before turning it on for a multi-track pipeline.

## Calibration-log output (`--calibration-log`)

Warnings from a calibration log are both printed to stderr *and* included
in the JSON output as `calibration_warnings` (an empty list when
everything's healthy). Read that field rather than parsing stderr if you're
consuming the output programmatically.

## Advanced input schema features

All optional, all backward compatible with plain numbers:

| Feature | How | Addresses |
|---|---|---|
| Non-stationary rejection rate/retries | `{"start": a, "end": b}` — interpolated linearly across the group's `position_factor` | agents plausibly get better/worse over a project; a constant r_i can't capture that |
| Context growth model | top-level `"context_model": "linear" \| "sublinear" \| "capped"` (+ optional `"context_cap"`) | linear CF overestimates cost for agents with context compression/summarization |
| Parallel pipelines | tag each group with `"track": "backend"` etc. — output reports per-track subtotals | ACEM's sequential-pipeline assumption doesn't fit fan-out/subagent architectures; run each track's `position_factor` relative to *its own* length, and set CF-reset (`position_factor` back near 0) at track boundaries if context isn't shared across tracks |
| LLM-perceived complexity | add `"llm_complexity_score"` (see `llm_complexity_score()`/`llm_complexity_tier()` helpers in the script) | human-judged Simple/Medium/Complex correlates weakly with actual token cost (paper's own cited evidence) — use this as a check on, not a replacement for, the human-judged tier |
| Calibration confidence/staleness | add `"sample_size"` and `"calibrated_date"` (YYYY-MM-DD) per group, or maintain a calibration log (`references/calibration_log_example.json`) and pass `--calibration-log path.json` | tells the reader whether a number is calibrated, a small pilot, or a cold-start guess, and flags constants overdue for recalibration or calibrated against a now-superseded agent version |

See `references/example_input_advanced.json` for a worked example
exercising all of these together.

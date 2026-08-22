# ACEM — condensed reference

Source: El-Ramly, M. "ACEM: A Cost Estimation Model for Agentic Software
Engineering." 2026. (2608.02582v1)

## Core formula

`Total_Cost = C_LLM + C_HITL + C_Infra` (additive, not hierarchical — relative
magnitude shifts with task complexity/autonomy, sometimes by an order of
magnitude between examples in the paper).

## C_LLM

```
C_LLM = Σ_i [ (T_in,i + T_out,i) × RF_i × CF_i ] × P_model
```
- `T_in,i + T_out,i = BaseTokens(type_i, complexity_i)` — calibrated per
  artifact type (Table 2: 10 types × 3 complexity levels = 30 constants,
  reducible to 5-8 via aggregation) and complexity (Simple/Medium/Complex,
  Table 1).
- `RF_i = 1 + (r_i × n_i)` — Revision Factor. r_i = rejection rate, n_i =
  avg retries per rejection.
- `CF_i = 1 + α × (i/N)` — Context Factor. Linear growth from position 1 to N
  in the pipeline; apply to task-intrinsic tokens only, never to
  already-context-inclusive API log totals (double-counts otherwise).

## C_HITL

```
C_HITL = C_review + C_rework
C_review = Σ_i (K_i × D_i × W)
C_rework  = Σ_i (r_i × RW_i × W)
```
K_i = review checkpoints (driven by HIS level), D_i = review duration, W =
fully loaded hourly rate, RW_i = rework duration.

## HITL Intensity Score (HIS) — Table 3/4

| HIS | Label | K_i | Context |
|---|---|---|---|
| 1 | Minimal | 1/epic | low-risk, validated agent |
| 2 | Standard | 1/story | typical business apps |
| 3 | Elevated | 1/task | safety-relevant, high complexity |
| 4 | Continuous | every action | safety-critical, regulated |

## C_Infra

`C_Infra = Σ_k U_k × P_k` — usage × unit price per resource (compute, storage,
tool-call APIs). Not a novel contribution of the paper; use standard cloud
cost estimation.

## Sizing-metric mappings (for prospective/planning use, not retrospective)

- UCP: `T_base,total = U_UCP × γ_UCP`
- Story Points: `T_base,total = SP_s × γ_SP × CW_s`
- Function Points: `T_base,total = FP × γ_FP`

γ constants are agent/domain-specific calibration constants, empirically
derived — not used in this skill's retrospective (codebase-first) mode.

## Calibration (Section 3.6)

4-step process requiring real pilot execution data: (1) pilot run ≥3 tasks per
artifact-type/complexity cell, (2) compute β (BaseTokens) as mean observed
tokens, (3) compute r_i, n_i, α from observed rejections/retries/position
regression, (4) derive γ constants by dividing observed totals by sizing-metric
values. **None of this has been done by the paper's authors** — all constants
are symbolic/placeholder. This skill's defaults (in SKILL.md) are informed
guesses, not calibrated values.

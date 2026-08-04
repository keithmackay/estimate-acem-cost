# Weaknesses of the ACEM Cost Estimation Model

Analysis of "ACEM: A Cost Estimation Model for Agentic Software Engineering"
(El-Ramly, 2026). The paper is unusually candid about its own limitations
(Sections 3.8, 4.3–4.4, 5, and the Conclusion) — much of this document builds
on gaps the authors themselves flag, plus additional gaps they don't.

## 1. It has never touched real data

This is the headline weakness, and the authors say so directly: "ACEM is
presented as a fully specified model structure and calibration methodology,
with constants left symbolic pending empirical grounding... it has not yet
been validated against real project data." Every β, γ, α, RF, and HIS→K_i
mapping in the paper is a placeholder. The two worked examples (Tables 5–6)
are explicitly "illustrative... for demonstration purposes only... not derived
from calibration." Until someone runs Section 3.6's calibration process on
real agentic pipelines, ACEM is a *shape* for a cost model, not a cost model —
no accuracy claim (MMRE, PRED(25), or otherwise) currently exists for it.

## 2. Missing pieces

- **No cost for task decomposition itself** (Assumption A2). ACEM assumes a
  project has already been broken into agent tasks before estimation starts.
  In practice, an agent (or human) doing that decomposition is itself a
  nontrivial cost — recursively, deciding how to decompose is a task subject
  to the same non-determinism ACEM is built to model, but it's outside the
  model's boundary.
- **No cost for planning/orchestration overhead.** The paper explicitly flags
  this as "one gap worth flagging" (Section 3.2.2): tool-call formulation and
  reflection steps are counted as agent actions but have no row in the
  BaseTokens table. Organizations are told to fold this into CF or invent a
  new category — i.e., the model doesn't actually account for it, it just
  tells you where to hide the slop.
- **No maintenance/long-run cost.** ACEM prices *building* the artifact, not
  owning it. The paper itself notes (Section 2.2) that AI-assisted code may
  have different long-term maintenance costs than human-written code, then
  never returns to the topic. For a codebase-cost retrospective (this skill's
  use case), that's a real gap: two codebases with identical ACEM-estimated
  build cost could have wildly different total cost of ownership.
- **No model for parallel/multi-agent pipelines** (Assumption A1). Real
  agentic systems increasingly run agents concurrently (subagents, fan-out
  patterns like the ones this very Claude Code session uses). ACEM's
  sequential-pipeline assumption doesn't just simplify this — it can't
  represent it at all; CF's "position in pipeline" concept has no clear
  analog when tasks run concurrently with partial context sharing.
- **No treatment of failed/abandoned projects.** All the machinery assumes a
  project reaches completion. Cost of a project an organization cancels
  partway through — arguably a *more* important number for a "should we
  build-vs-buy with agents" decision — isn't modeled.

## 3. Assumptions that may not hold

- **Additivity of C_LLM + C_HITL + C_Infra (A6).** The paper admits this is "a
  pragmatic simplification rather than a claim of strict independence,"
  explicitly calling out that infrastructure failures triggering additional
  LLM retries isn't modeled. Rejection events already reach across
  C_LLM/C_HITL by design (shared r_i) — the model works *despite* not being
  additive, patched together with special-case reasoning (Section 3.1's
  discussion of why rejection doesn't double-count). That patched-together
  quality suggests the three-term sum is a presentational convenience more
  than a structural truth, and further cross-terms may exist unmodeled.
- **Stationary rejection rates (A3).** RF assumes r_i is constant across a
  project. But the paper's own related-work review notes agent accuracy
  varies with context length and accumulated codebase familiarity — an agent
  plausibly gets *better* at a codebase over the course of a project (more
  context, more established patterns) or *worse* (context rot, drift). A
  constant r_i can't capture either trend.
- **Linear context growth (Eq. 7).** CF assumes token cost grows linearly with
  pipeline position. The authors flag this as "a simplifying assumption" and
  note real growth may be non-linear depending on context compression,
  summarization, or sliding-window techniques — techniques that are becoming
  the default in production agent harnesses, not the exception. A linear
  model calibrated on an agent without context management will systematically
  overestimate cost for one that has it, and vice versa.
- **Construct separability (A8).** BaseTokens, RF, CF, and CW are calibrated
  independently, but the paper concedes complexity may drive several of them
  at once (a complex task shows both higher BaseTokens *and* higher rejection
  rate). If they're capturing overlapping variance rather than independent
  effects, calibration can silently double-count the same underlying signal
  across two constants — and the model structure gives no way to detect this
  without controlled experiments the paper doesn't propose running.
- **Parameter identifiability (A7).** The calibration process asks
  organizations to separately estimate rejection rate, retry count, and
  context coefficient from pilot data. Without fine-grained instrumentation
  distinguishing these three phenomena, "multiple parameter combinations
  could fit the same observed cost equally well" — the paper's own words.
  Most organizations attempting a first calibration will not have this
  instrumentation and will produce confounded, non-identifiable constants
  while believing they're calibrated.
- **Human-perceived complexity (Table 1) predicts LLM-perceived cost.** The
  paper itself undercuts this: it cites evidence (Bai et al.) that token
  consumption correlates weakly with conventional task difficulty, and Xie et
  al. showing classical complexity metrics don't correlate with LLM task
  performance after controlling for length. Table 1/2's entire organizing
  axis (Simple/Medium/Complex as a human would judge it) is explicitly
  acknowledged as "an unreliable proxy" for the thing it's meant to predict.
  That's a foundational scoping choice built on a relationship the authors
  say doesn't reliably hold.
- **Reviewer homogeneity (A5), single-rate W.** Real HITL cost blends a junior
  reviewer doing routine approvals with a senior engineer escalation-reviewing
  a security-relevant diff. Collapsing this to one hourly rate understates
  cost concentration in the cases that matter most (Complex/HIS-4 tasks are
  exactly where a below-average blended rate most understates true cost).

## 4. What will change model-to-model and vendor-to-vendor (and break calibration fast)

- **Every calibration constant is agent- and version-specific by design**
  (Assumption A4, explicit in the paper). β, RF, and CF must be recalibrated
  whenever the underlying model changes. Given the pace of model releases
  (the paper itself references Claude Sonnet 5 "promotional pricing through
  Aug 31, 2026" in its own worked example — a pricing regime with a built-in
  expiration date), any organization's calibrated ACEM constants have a
  shelf life measured in months, not years, unlike COCOMO II's calibration
  constants which stayed roughly stable for a decade-plus.
- **Pricing structure itself is unstable across vendors.** Input/output token
  pricing, prompt-caching discounts (41–80% reduction per Lumer et al., cited
  in the paper), batch pricing, and model-routing all shift the effective
  P_model term independent of any underlying capability change. A 2x price
  change from a vendor (which has happened repeatedly in the LLM market)
  invalidates C_LLM estimates instantly, without any change in RF/CF/β.
- **Reasoning/"thinking" modes and agentic harness design change token
  consumption structurally, not just quantitatively.** The paper notes
  extended reasoning chains and retrieval both inflate token counts in ways
  unrelated to task complexity. As vendors ship new agent-harness patterns
  (subagent fan-out, tool-result caching, context compaction), the very
  definition of "one agent action" that BaseTokens is denominated in shifts
  under the model's feet.
- **Success rates on SWE-bench-style benchmarks — the paper's suggested cold-
  start RF source — are rising quickly across model generations.** An RF
  estimate calibrated against a 2025 model's 55% success rate is stale within
  a year against models clearing 80%+. The model's own suggested bootstrap
  mechanism (Section 4.4, "Benchmark-based initialization") is therefore a
  moving target, and the paper admits this data isn't even published in the
  needed form yet ("currently more aspirational than actionable").
- **HITL norms (HIS thresholds, org tolerance for autonomous agents) will
  shift over time** as trust in agents grows or high-profile failures set it
  back — this is a social/organizational variable, not a technical one, and
  ACEM has no mechanism to track it except manual reclassification.

## 5. What would meaningfully improve the model

1. **Publish the calibration dataset the paper calls for (Section 5.1) before
   anything else.** Every other weakness is downstream of "no real data
   exists yet." A multi-org, multi-agent calibration dataset is the single
   highest-leverage next step, as the authors themselves conclude. *Not
   implementable by tooling alone — requires real pilot execution data from
   organizations running agentic pipelines. The calculator below accepts
   such data once collected (`sample_size`/`calibrated_date` per constant)
   but cannot manufacture it.*
2. **Replace point estimates with distributions.** ✅ *Implemented* — the
   skill's calculator supports `--montecarlo N`, accepting `{low, mode, high}`
   triangular distributions for `rejection_rate`, `retries_per_rejection`,
   and `alpha`, returning p10/p50/p90/mean/stdev instead of a single figure.
3. **Model non-stationary rejection rates and sub-linear/capped context
   growth.** ✅ *Implemented* — `rejection_rate`/`retries_per_rejection`
   accept `{"start": a, "end": b}` linear interpolation across pipeline
   position; `context_model` accepts `linear` / `sublinear` / `capped` (with
   an optional `context_cap`).
4. **Decouple the model from human-perceived complexity as the primary
   axis.** ✅ *Implemented* — `llm_complexity_score()`/`llm_complexity_tier()`
   in the calculator compute a model-facing complexity signal (length +
   reasoning/retrieval overhead) that can be attached per group and compared
   against the human-judged Simple/Medium/Complex tier, rather than trusting
   the human tier alone.
5. **Add a parallel-pipeline extension.** ✅ *Implemented* — groups can be
   tagged with a `track`, and the calculator reports per-track cost
   subtotals; organizations set each track's `position_factor` relative to
   its own length (and reset it near 0 at track boundaries when context
   isn't shared) to approximate fan-out/subagent architectures ACEM's
   sequential model can't otherwise represent.
6. **Track calibration decay explicitly.** ✅ *Implemented* — `--calibration-log`
   reads a log of calibrated constants and flags entries below a minimum
   pilot sample size, older than a freshness threshold, or calibrated
   against an agent version that's since changed.
7. **Give the model a self-reported confidence/staleness indicator.** ✅
   *Implemented* — every group in the calculator's output carries a
   `confidence` label (`cold-start` / `partial` / `calibrated`, derived from
   `sample_size`) and a `calibration_age_days` figure when a
   `calibrated_date` is supplied, so a calibrated number and a cold-start
   guess no longer look identical in the output.

Implementation: `~/.claude/skills/acem-cost-estimation/acem_calculate.py` and
`SKILL.md`. See `references/example_input_advanced.json` for a worked example
exercising all of #2–#7 together.

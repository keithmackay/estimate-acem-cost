# Opportunities to Strengthen the ACEM Cost Estimation Model

Analysis of "ACEM: A Cost Estimation Model for Agentic Software Engineering"
(El-Ramly, 2026; [arXiv:2608.02582](https://arxiv.org/abs/2608.02582)). The
paper is unusually candid about its own limitations (Sections 3.8, 4.3–4.4, 5,
and the Conclusion) — much of this document builds on opportunities the
authors themselves flag, plus additional ones they don't. Framed as
opportunities for improvement, not as a takedown: ACEM is presented by its
authors as a first-draft structure inviting community validation, and this
document is written in that spirit.

## 1. The biggest opportunity: real calibration data

This is the headline opportunity, and the authors say so directly: "ACEM is
presented as a fully specified model structure and calibration methodology,
with constants left symbolic pending empirical grounding... it has not yet
been validated against real project data." Every β, γ, α, RF, and HIS→K_i
mapping in the paper is a placeholder. The two worked examples (Tables 5–6)
are explicitly "illustrative... for demonstration purposes only... not derived
from calibration." Once someone runs Section 3.6's calibration process on
real agentic pipelines, ACEM moves from a *shape* for a cost model to an
actual cost model with a real accuracy claim (MMRE, PRED(25), or otherwise) —
that step is the single highest-leverage thing that could happen to it next.

## 2. Pieces the model could extend to cover

- **Cost of task decomposition itself** (Assumption A2). ACEM assumes a
  project has already been broken into agent tasks before estimation starts.
  In practice, an agent (or human) doing that decomposition is itself a
  nontrivial cost — recursively, deciding how to decompose is a task subject
  to the same non-determinism ACEM is built to model, but it's currently
  outside the model's boundary and could be brought inside it.
- **Planning/orchestration overhead.** The paper explicitly flags this as
  "one gap worth flagging" (Section 3.2.2): tool-call formulation and
  reflection steps are counted as agent actions but have no row in the
  BaseTokens table. Organizations are told to fold this into CF or invent a
  new category — a workable stopgap, but a dedicated category would make this
  cost visible rather than absorbed into another term.
- **Maintenance/long-run cost.** ACEM prices *building* the artifact, not
  owning it. The paper itself notes (Section 2.2) that AI-assisted code may
  have different long-term maintenance costs than human-written code, an
  angle it doesn't return to. For a codebase-cost retrospective (this skill's
  use case), extending to total cost of ownership would let two codebases
  with identical ACEM-estimated build cost be told apart on the metric that
  often matters more.
- **Parallel/multi-agent pipelines** (Assumption A1). Real agentic systems
  increasingly run agents concurrently (subagents, fan-out patterns like the
  ones this very Claude Code session uses). ACEM's sequential-pipeline
  assumption doesn't yet represent this; CF's "position in pipeline" concept
  would need a concurrent-context analog to extend cleanly to fan-out
  architectures.
- **Failed/abandoned projects.** All the machinery assumes a project reaches
  completion. Modeling the cost of a project an organization cancels partway
  through — arguably a *very* useful number for a "should we build-vs-buy
  with agents" decision — is an open extension.

## 3. Assumptions worth stress-testing

- **Additivity of C_LLM + C_HITL + C_Infra (A6).** The paper is explicit that
  this is "a pragmatic simplification rather than a claim of strict
  independence," noting that infrastructure failures triggering additional
  LLM retries isn't currently modeled. Rejection events already reach across
  C_LLM/C_HITL by design (shared r_i), handled through careful special-case
  reasoning (Section 3.1's discussion of why rejection doesn't double-count).
  Formalizing any remaining cross-terms would strengthen the case that the
  three-term sum is a structural truth rather than a presentational
  convenience.
- **Stationary rejection rates (A3).** RF assumes r_i is constant across a
  project. The paper's own related-work review notes agent accuracy varies
  with context length and accumulated codebase familiarity — an agent
  plausibly gets *better* at a codebase over the course of a project (more
  context, more established patterns) or *worse* (context rot, drift). A
  time-varying r_i could capture either trend; the skill in this repo already
  supports this via non-stationary `{start, end}` rejection rates.
- **Linear context growth (Eq. 7).** CF assumes token cost grows linearly with
  pipeline position. The authors flag this as "a simplifying assumption" and
  note real growth may be non-linear depending on context compression,
  summarization, or sliding-window techniques — techniques that are becoming
  the default in production agent harnesses. Offering sublinear/capped growth
  curves as first-class options (as this repo's calculator now does) helps
  the model fit agents with active context management.
- **Construct separability (A8).** BaseTokens, RF, CF, and CW are calibrated
  independently, but the paper notes complexity may drive several of them at
  once (a complex task can show both higher BaseTokens *and* higher rejection
  rate). Controlled experiments isolating each construct's independent
  contribution — something the paper doesn't yet propose running — would
  clarify whether they're capturing distinct variance or overlapping signal.
- **Parameter identifiability (A7).** The calibration process asks
  organizations to separately estimate rejection rate, retry count, and
  context coefficient from pilot data. Without fine-grained instrumentation
  distinguishing these three phenomena, "multiple parameter combinations
  could fit the same observed cost equally well" — the paper's own words.
  Organizations attempting a first calibration will want that
  instrumentation in place from day one to get identifiable, trustworthy
  constants.
- **Human-perceived complexity (Table 1) as a proxy for LLM-perceived cost.**
  The paper itself surfaces evidence worth weighing here: Bai et al. found
  token consumption correlates weakly with conventional task difficulty, and
  Xie et al. found classical complexity metrics don't correlate with LLM
  task performance after controlling for length. The paper names a
  complementary "LLM-perceived complexity" dimension but doesn't fully
  operationalize it — doing so (as this repo's `llm_complexity_score()`
  attempts) would give Table 1/2's Simple/Medium/Complex axis a
  model-facing check.
- **Reviewer homogeneity (A5), single-rate W.** Real HITL cost blends a
  junior reviewer doing routine approvals with a senior engineer
  escalation-reviewing a security-relevant diff. A tiered or role-weighted W
  would capture cost concentration in the highest-stakes cases (Complex/
  HIS-4 tasks) more precisely than a single blended rate.

## 4. What will need active tracking as models and vendors evolve

- **Calibration constants are agent- and version-specific by design**
  (Assumption A4, explicit in the paper). β, RF, and CF need recalibrating
  whenever the underlying model changes. Given the pace of model releases
  (the paper itself references Claude Sonnet 5 "promotional pricing through
  Aug 31, 2026" in its own worked example — a pricing regime with a built-in
  expiration date), organizations should expect their calibrated ACEM
  constants to have a shelf life measured in months, unlike COCOMO II's
  constants, which stayed roughly stable for a decade-plus. A recalibration
  cadence built into adoption plans from the start would help.
- **Pricing structure shifts across vendors.** Input/output token pricing,
  prompt-caching discounts (41–80% reduction per Lumer et al., cited in the
  paper), batch pricing, and model-routing all move the effective P_model
  term independent of any underlying capability change. Tracking pricing
  changes as a distinct trigger for re-estimation (separate from
  recalibrating RF/CF/β) would keep C_LLM estimates current.
- **Reasoning/"thinking" modes and agentic harness design change token
  consumption structurally, not just quantitatively.** The paper notes
  extended reasoning chains and retrieval both inflate token counts in ways
  unrelated to task complexity. As vendors ship new agent-harness patterns
  (subagent fan-out, tool-result caching, context compaction), the
  definition of "one agent action" that BaseTokens is denominated in will
  keep shifting — worth revisiting BaseTokens categories periodically as
  harness patterns evolve.
- **Benchmark success rates — the paper's suggested cold-start RF source —
  are rising quickly across model generations.** An RF estimate calibrated
  against one model generation's success rate can go stale within a year as
  newer models clear higher benchmarks. The model's own suggested bootstrap
  mechanism (Section 4.4, "Benchmark-based initialization") will get more
  useful as SWE-bench-style benchmarks begin publishing token-consumption
  data alongside success rates, not just success rates alone ("currently
  more aspirational than actionable," per the paper).
- **HITL norms (HIS thresholds, org tolerance for autonomous agents) will
  shift over time** as trust in agents grows or high-profile failures set it
  back — a social/organizational variable, not a technical one. Building in
  a periodic HIS-classification review would keep pace with that shift.

## 5. Concrete improvements applied in this repo

1. **A real calibration dataset (Section 5.1 of the paper).** Every other
   opportunity here is downstream of "no real data exists yet" — a
   multi-org, multi-agent calibration dataset is the single highest-leverage
   next step, as the authors themselves conclude. *Not implementable by
   tooling alone — requires real pilot execution data from organizations
   running agentic pipelines. The calculator in this repo accepts such data
   once collected (`sample_size`/`calibrated_date` per constant) but can't
   manufacture it.*
2. **Distributions instead of point estimates.** ✅ *Implemented* — the
   skill's calculator supports `--montecarlo N`, accepting `{low, mode, high}`
   triangular distributions for `rejection_rate`, `retries_per_rejection`,
   and `alpha`, returning p10/p50/p90/mean/stdev instead of a single figure.
3. **Non-stationary rejection rates and sub-linear/capped context growth.**
   ✅ *Implemented* — `rejection_rate`/`retries_per_rejection` accept
   `{"start": a, "end": b}` linear interpolation across pipeline position;
   `context_model` accepts `linear` / `sublinear` / `capped` (with an
   optional `context_cap`).
4. **A model-facing complexity axis alongside human-perceived complexity.**
   ✅ *Implemented* — `llm_complexity_score()`/`llm_complexity_tier()` in the
   calculator compute a model-facing complexity signal (length +
   reasoning/retrieval overhead) that can be attached per group and compared
   against the human-judged Simple/Medium/Complex tier.
5. **A parallel-pipeline extension.** ✅ *Implemented* — groups can be
   tagged with a `track`, and the calculator reports per-track cost
   subtotals; organizations set each track's `position_factor` relative to
   its own length (and reset it near 0 at track boundaries when context
   isn't shared) to approximate fan-out/subagent architectures.
6. **Explicit calibration-decay tracking.** ✅ *Implemented* —
   `--calibration-log` reads a log of calibrated constants and flags entries
   below a minimum pilot sample size, older than a freshness threshold, or
   calibrated against an agent version that's since changed.
7. **A self-reported confidence/staleness indicator.** ✅ *Implemented* —
   every group in the calculator's output carries a `confidence` label
   (`cold-start` / `partial` / `calibrated`, derived from `sample_size`) and
   a `calibration_age_days` figure when a `calibrated_date` is supplied, so a
   calibrated number and a cold-start guess no longer look identical in the
   output.

Implementation: `skill/acem-cost-estimation/acem_calculate.py` and
`skill/acem-cost-estimation/SKILL.md`. See
`skill/acem-cost-estimation/references/example_input_advanced.json` for a
worked example exercising all of #2–#7 together.

> [!NOTE]
> This document, the paper, and the accompanying skill are exploratory and
> testing material. No cost figure produced by this repo's tooling should be
> treated as a validated or guaranteed estimate of real-world agentic
> development cost.

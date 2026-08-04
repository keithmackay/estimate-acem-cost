# Implementation Plan — improve-this findings (2026-08-04)

Source review: `docs/reviews/2026-08-04-improve-this.md`. Covers all 10
findings, phased by dependency and risk. Each phase is independently
shippable — commit after each.

---

## Phase 1 — Eliminate the duplicate skill tree (Finding #1)

**Problem**: `skill/acem-cost-estimation/skills/acem-cost-estimation/` is a
manually-maintained byte-copy of the root skill files for Codex/Gemini.
Nothing keeps the two in sync.

**Approach**: Replace the copy with a generation step, not a second
hand-maintained copy.

1. Write a small script, `skill/acem-cost-estimation/scripts/sync_ports.sh`
   (or a `Makefile` target), that `rsync`s the canonical root files
   (`SKILL.md`, `acem_calculate.py`, `references/`) into
   `skills/acem-cost-estimation/` — i.e., codify the manual rsync already
   used during development instead of relying on remembering to run it.
2. Add a CI-less but discoverable guard: a one-line check in the script
   (`diff -rq` between root and the nested copy) that exits non-zero if
   they've drifted, so running the script is also a way to detect drift
   before it's fixed.
3. Update `skill/acem-cost-estimation/README.md`'s Codex/Gemini install
   sections to mention that `skills/acem-cost-estimation/` is generated —
   run `scripts/sync_ports.sh` after editing `SKILL.md` or
   `acem_calculate.py`, not edited directly.
4. Run the script once to confirm it reproduces the current (already
   in-sync) state exactly (`diff -rq` should report no differences).

**Test plan**: After editing `SKILL.md` (make a trivial whitespace change),
confirm the guard script detects drift; run the sync script; confirm drift
is gone.

**Docs to touch**: `skill/acem-cost-estimation/README.md` (Codex/Gemini CLI
install sections).

---

## Phase 2 — Add a test suite for the calculator (Finding #2)

**Problem**: `acem_calculate.py` has zero automated tests.

1. Create `skill/acem-cost-estimation/tests/test_acem_calculate.py` using
   `unittest` (stdlib only, consistent with the calculator's
   zero-dependency design — don't introduce pytest as a new dependency
   unless the user prefers it).
2. Cover, at minimum:
   - `_resolve`/`_sample`: constant, `{start,end}`, `{low,mode,high}` shapes.
   - `context_factor`: linear, sublinear, capped, and the capped-with-no-cap
     fallback (`cap=None` → uses `alpha` as ceiling).
   - `acem_cost`: reproduce this repo's `references/example_input.json`
     output exactly (regression test against the known-good numbers
     verified during development — e.g. `Total_Cost: 3184.0`) to lock in
     current behavior before any other phase changes it.
   - `acem_cost_monte_carlo`: with a fixed `seed`, assert p10 ≤ p50 ≤ p90
     and that percentiles fall within the min/max of the underlying
     triangular distributions' bounds.
   - `check_calibration_log`: underpowered sample, stale date, and
     agent-version-mismatch each produce exactly one warning; a fully
     healthy entry produces none (mirrors the manual check already run
     this session against `references/calibration_log_example.json`).
   - `confidence_label` / `staleness_days`: boundary values (`sample_size`
     of exactly 3 and 10; `calibrated_date` of `None`).
3. Add a one-line `## Development` note in `skill/acem-cost-estimation/README.md`
   pointing to `python3 -m unittest discover tests`.

**Test plan**: `python3 -m unittest discover skill/acem-cost-estimation/tests`
passes; intentionally break one formula (e.g. flip a `+`/`-`) and confirm
the regression test catches it, then revert.

**Docs to touch**: `skill/acem-cost-estimation/README.md` (Development
section, new).

---

## Phase 3 — Accuracy & consistency fixes (Findings #3, #4, #8)

Do these together since they're all documentation/code-accuracy touch-ups
to the same two files.

1. **#3 — Fix the "Full paper" mislabel.** In `SKILL.md`, change
   `Full paper: references/acem-paper-summary.md` to something like
   `Condensed formula reference: references/acem-paper-summary.md
   (full paper: docs/2608.02582v1.pdf in the parent repo — not bundled
   with a standalone skill install)`. This is an honest label, not a fix
   to bundle the 1.4MB PDF into every platform port (that's a separate,
   larger decision — flag it to the user rather than deciding unilaterally
   whether the PDF should ship with the skill).
2. **#4 — Align alpha resolution between point-estimate and Monte Carlo.**
   In `acem_cost_monte_carlo` (line ~249), replace the hardcoded
   `_sample(alpha_spec, 0.5, rng)` with per-group resolution matching
   `acem_cost`'s pattern — sample/resolve alpha inside the per-group loop
   using that group's own `pos`, same as `acem_cost` does. Since alpha is
   typically constant across groups in practice, this changes behavior
   only for the currently-undocumented non-stationary-alpha edge case;
   confirm with the regression test from Phase 2 that constant-alpha inputs
   produce identical output before and after.
3. **#8 — Mention CF's alternative growth models where CF is first
   introduced.** In `SKILL.md` Step 4 ("Estimate CF"), add a one-line
   pointer immediately after the linear formula: "This is the paper's
   default linear model; `sublinear`/`capped` alternatives exist — see
   `context_model` in Step 7." Keeps the full explanation where it already
   lives (Step 7's table) without duplicating it, just adds a forward
   pointer at first mention.

**Test plan**: Re-run Phase 2's test suite after the alpha change; manually
diff `SKILL.md` rendering to confirm no broken cross-references.

**Docs to touch**: `SKILL.md`, `acem_calculate.py`.

---

## Phase 4 — Completeness gaps (Findings #6, #9)

**Before starting**: #6 (Monte Carlo losing per-group/track detail) is
flagged Medium/Medium specifically because it might be an intentional scope
choice, not an oversight. Confirm with the user whether Monte Carlo should
gain per-group/per-track distributions, or whether aggregate-only is fine
and this finding should be closed as "working as intended" — don't build
this speculatively.

If confirmed as a real gap:

1. Extend `acem_cost_monte_carlo` to accumulate per-group and per-track
   totals across samples (parallel arrays keyed by group name / track name,
   same pattern as the existing `totals`/`llm_totals`/`hitl_totals` lists),
   and return `groups: {name: {p10, p50, p90}}` and `tracks: {name: {...}}`
   alongside the existing aggregate output.
2. Update the Phase 2 test suite to cover the new per-group/per-track MC
   output shape.
3. Update `SKILL.md` Step 7's Monte Carlo section to mention the
   per-group/per-track breakdown is now available.

For #9 (calibration warnings not in JSON output):

1. Change `check_calibration_log`'s call site in `main()` to attach the
   returned warnings list to the output dict as `calibration_warnings`
   (empty list if none) before printing, rather than only printing to
   stderr. Keep the stderr printing too, for interactive use.
2. Update the Phase 2 test suite to assert the new field's presence/shape.

**Docs to touch**: `SKILL.md` (Step 7).

---

## Phase 5 — Token efficiency pass on SKILL.md (Finding #7)

This finding is specifically about always-loaded content that's only
situationally needed. Per project convention, use the dedicated skills for
this rather than doing it ad hoc:

1. The "Other advanced input features" table (non-stationary params,
   context models, parallel pipelines, LLM-complexity, calibration log) is
   reference material, not core workflow — move it out of `SKILL.md` into
   a new `skill/acem-cost-estimation/references/advanced-features.md`, and
   replace it in `SKILL.md` with a one-line pointer: "For non-stationary
   inputs, alternative context-growth curves, parallel pipelines, an
   LLM-complexity axis, or calibration-log tracking, see
   `references/advanced-features.md`."
2. Run **`/plsfix`** on the resulting `SKILL.md` (and
   `references/advanced-features.md`) to do the clarity/token-efficiency
   pass on what remains — this is exactly the kind of "make the always-loaded
   instructions tighter" work `/plsfix` is designed for, so use it rather
   than manually rewriting prose.
3. This project's README material is already appropriately separated
   (`skill/acem-cost-estimation/README.md` for install/compat, the root
   `README.md` for project overview) — no `/readme` re-run is needed here,
   since this finding is about moving *reference* content, not *setup/usage*
   content, out of SKILL.md.
4. Re-sync the Codex/Gemini port (Phase 1's script) after this edit, since
   it changes `SKILL.md` and adds a new `references/` file.
5. Re-run the Phase 2 test suite to confirm the calculator itself is
   untouched by this doc-only phase.

**Docs to touch**: `SKILL.md`, new `references/advanced-features.md`.

---

## Phase 6 — Minor code efficiency cleanup (Finding #10)

Small enough to fold in wherever convenient (e.g., alongside Phase 3's
alpha-consistency fix, since both touch the same lines):

1. In `acem_cost`, resolve `alpha` once before the `for g in groups` loop
   when `alpha_spec` is a plain `int`/`float` (skip the per-group
   `_resolve` call in that case); leave the per-group resolution path for
   dict specs (`{start,end}` or `{low,mode,high}`) since those genuinely
   may vary by position.
2. Confirm via the Phase 2 regression test that output is byte-identical
   before/after for the existing example inputs.

**Docs to touch**: none (code-only, behavior-preserving).

---

## Suggested Commit Sequence

1. Phase 1 (redundancy/sync tooling)
2. Phase 2 (test suite) — do this early since every later phase should be
   verified against it
3. Phase 3 (accuracy fixes, small)
4. Phase 4 (completeness — confirm scope with user before building #6)
5. Phase 5 (`/plsfix` token-efficiency pass)
6. Phase 6 (folded into Phase 3's commit, or standalone if preferred)

After each phase: run the test suite, run the Codex/Gemini sync/drift-check
from Phase 1, and commit with a message describing which finding number(s)
it addresses.

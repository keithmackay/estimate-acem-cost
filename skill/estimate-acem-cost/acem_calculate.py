#!/usr/bin/env python3
"""
ACEM calculator — computes C_LLM, C_HITL, C_Infra, and Total_Cost
per "ACEM: A Cost Estimation Model for Agentic Software Engineering" (El-Ramly, 2026),
extended per the improvements in ACEM_OPPORTUNITIES.md section 5:

  #2  Monte Carlo cost distributions instead of a single point estimate
  #3  non-stationary rejection rates (start/end interpolation) and
      alternative context-growth curves (linear / sublinear / capped)
  #4  optional LLM-perceived complexity score, tracked alongside the
      human-perceived Simple/Medium/Complex axis
  #5  parallel-pipeline support (per-track subtotals + isolated-context CF)
  #6  #7  calibration confidence/staleness reporting per group, backed by
      an external calibration log

Input schema (see references/example_input.json and
references/example_input_advanced.json): a JSON task list (one entry per
artifact-type/complexity group) plus pricing/rate/pipeline parameters.

Any of rejection_rate, retries_per_rejection, and alpha may be given as:
  - a plain number                              (constant, as before)
  - {"start": a, "end": b}                      (non-stationary, linear
                                                  interpolation over the
                                                  group's position_factor)
  - {"low": a, "mode": m, "high": b}             (triangular distribution,
                                                  used by --montecarlo;
                                                  point mode uses `m`)

This is arithmetic only — it does not decide the input counts or which
defaults to use. See SKILL.md for how to derive inputs from a codebase and
for the default constant tables (Section 3.2.2/3.2.3/3.2.4 equivalents).
"""
import argparse
import json
import random
import statistics
import sys
from datetime import date, datetime


# ---------------------------------------------------------------------------
# Parameter resolution — supports constants, non-stationary interpolation,
# and (for Monte Carlo) triangular-distribution sampling. (Improvements #2, #3)
# ---------------------------------------------------------------------------

def _resolve(spec, position_factor):
    """Point-estimate resolution: constant, non-stationary mean, or a
    distribution's mode."""
    if isinstance(spec, (int, float)):
        return float(spec)
    if isinstance(spec, dict):
        if "start" in spec and "end" in spec:
            return spec["start"] + (spec["end"] - spec["start"]) * position_factor
        if "mode" in spec:
            return float(spec["mode"])
        if "value" in spec:
            return float(spec["value"])
    raise ValueError(f"Unrecognized parameter spec: {spec!r}")


def _sample(spec, position_factor, rng):
    """Monte Carlo resolution: draws from a triangular distribution when
    {low, mode, high} is given; otherwise same as _resolve (non-stationary
    interpolation is treated as deterministic structure, not noise)."""
    if isinstance(spec, dict) and "low" in spec and "high" in spec:
        mode = spec.get("mode", (spec["low"] + spec["high"]) / 2)
        return rng.triangular(spec["low"], spec["high"], mode)
    return _resolve(spec, position_factor)


# ---------------------------------------------------------------------------
# Context factor models. (Improvement #3)
# ---------------------------------------------------------------------------

def context_factor(alpha, position_factor, model="linear", cap=None):
    if model == "linear":
        return 1 + alpha * position_factor
    if model == "sublinear":
        return 1 + alpha * (position_factor ** 0.5)
    if model == "capped":
        ceiling = cap if cap is not None else alpha
        return 1 + min(alpha * position_factor, ceiling)
    raise ValueError(f"Unknown context growth model: {model!r}")


# ---------------------------------------------------------------------------
# LLM-perceived complexity — a secondary axis alongside human-perceived
# Simple/Medium/Complex, since the paper's own cited evidence (Bai et al.,
# Xie et al.) says human-judged complexity correlates weakly with actual
# token/resource consumption. Use this to sanity-check or override the
# BaseTokens tier chosen by human judgment alone. (Improvement #4)
# ---------------------------------------------------------------------------

def llm_complexity_score(avg_input_tokens, avg_output_tokens,
                          reasoning_steps=1, retrieval_calls=0):
    """Rough model-facing complexity score. Not a calibrated constant — a
    triage heuristic for picking/checking a BaseTokens tier. Weights are
    illustrative: length dominates, reasoning/retrieval add multiplicatively
    per the paper's Section 3.2.2 discussion of what actually drives token
    burden (length, context growth, reasoning chains, retrieval)."""
    length_component = avg_input_tokens + 3 * avg_output_tokens  # output priced/weighted higher
    overhead_multiplier = 1 + 0.15 * (reasoning_steps - 1) + 0.25 * retrieval_calls
    return round(length_component * overhead_multiplier)


def llm_complexity_tier(score, simple_max=15000, medium_max=60000):
    if score <= simple_max:
        return "Simple"
    if score <= medium_max:
        return "Medium"
    return "Complex"


# ---------------------------------------------------------------------------
# Calibration confidence / staleness. (Improvements #6, #7)
# ---------------------------------------------------------------------------

def confidence_label(sample_size):
    if sample_size is None or sample_size < 3:
        return "cold-start (uncalibrated default)"
    if sample_size < 10:
        return "partial (small pilot sample)"
    return "calibrated"


def staleness_days(calibrated_date_str, today=None):
    if not calibrated_date_str:
        return None
    d = datetime.strptime(calibrated_date_str, "%Y-%m-%d").date()
    today = today or date.today()
    return (today - d).days


def check_calibration_log(log_path, max_age_days=90, min_samples=3):
    """Read a calibration log (see references/calibration_log_example.json)
    and flag entries that are stale or underpowered. Returns a list of
    warning strings — empty if everything looks solid."""
    with open(log_path) as f:
        log = json.load(f)
    warnings = []
    for entry in log.get("constants", []):
        name = entry.get("name", "<unnamed>")
        n = entry.get("sample_size")
        age = staleness_days(entry.get("calibrated_date"))
        if n is None or n < min_samples:
            warnings.append(f"{name}: only {n} pilot samples (< {min_samples}) — {confidence_label(n)}")
        if age is not None and age > max_age_days:
            warnings.append(f"{name}: calibrated {age} days ago (> {max_age_days}) — due for recalibration")
        if entry.get("agent_version") and entry.get("current_agent_version") and \
                entry["agent_version"] != entry["current_agent_version"]:
            warnings.append(f"{name}: calibrated against agent version {entry['agent_version']!r}, "
                             f"currently running {entry['current_agent_version']!r} — recalibrate")
    return warnings


# ---------------------------------------------------------------------------
# Core cost calculation (point estimate). Backward compatible with the
# original plain-float input schema.
# ---------------------------------------------------------------------------

def acem_cost(groups, alpha_spec, price_in_per_m, price_out_per_m,
              reviewer_rate, infra_cost=0.0, context_model="linear",
              context_cap=None):
    results = []
    tracks = {}
    total_llm = 0.0
    total_hitl = 0.0
    # alpha is pipeline-level, not group-level: when given as a plain
    # constant it doesn't vary by position, so resolve it once rather than
    # redundantly on every group. Dict specs ({start,end} or
    # {low,mode,high}) may genuinely vary by position, so those still
    # resolve per group inside the loop.
    static_alpha = alpha_spec if isinstance(alpha_spec, (int, float)) else None

    for g in groups:
        pos = g.get("position_factor", 0.5)
        track = g.get("track", "main")

        rejection_rate = _resolve(g["rejection_rate"], pos)
        retries = _resolve(g["retries_per_rejection"], pos)
        alpha = static_alpha if static_alpha is not None else _resolve(alpha_spec, pos)

        rf = 1 + (rejection_rate * retries)
        cf = context_factor(alpha, pos, model=context_model, cap=context_cap)

        in_tokens = g["base_in"] * g["count"] * rf * cf
        out_tokens = g["base_out"] * g["count"] * rf * cf

        c_llm = (in_tokens * price_in_per_m / 1_000_000) + \
                (out_tokens * price_out_per_m / 1_000_000)

        c_review = g["count"] * g["review_checkpoints_per_unit"] * \
            g["review_hours"] * reviewer_rate
        c_rework = g["count"] * rejection_rate * \
            g["rework_hours"] * reviewer_rate
        c_hitl = c_review + c_rework

        total_llm += c_llm
        total_hitl += c_hitl

        track_totals = tracks.setdefault(track, {"C_LLM": 0.0, "C_HITL": 0.0})
        track_totals["C_LLM"] += c_llm
        track_totals["C_HITL"] += c_hitl

        entry = {
            "name": g["name"],
            "track": track,
            "count": g["count"],
            "RF": round(rf, 3),
            "CF": round(cf, 3),
            "adjusted_input_tokens": round(in_tokens),
            "adjusted_output_tokens": round(out_tokens),
            "C_LLM": round(c_llm, 2),
            "C_review": round(c_review, 2),
            "C_rework": round(c_rework, 2),
            "C_HITL": round(c_hitl, 2),
            "confidence": confidence_label(g.get("sample_size")),
        }
        if "llm_complexity_score" in g:
            entry["llm_complexity_score"] = g["llm_complexity_score"]
            entry["llm_complexity_tier"] = llm_complexity_tier(g["llm_complexity_score"])
        if g.get("calibrated_date"):
            entry["calibration_age_days"] = staleness_days(g["calibrated_date"])
        results.append(entry)

    total = total_llm + total_hitl + infra_cost

    return {
        "groups": results,
        "tracks": {k: {"C_LLM": round(v["C_LLM"], 2), "C_HITL": round(v["C_HITL"], 2),
                       "subtotal": round(v["C_LLM"] + v["C_HITL"], 2)}
                   for k, v in tracks.items()},
        "C_LLM_total": round(total_llm, 2),
        "C_HITL_total": round(total_hitl, 2),
        "C_Infra": round(infra_cost, 2),
        "Total_Cost": round(total, 2),
        "C_LLM_share_pct": round(100 * total_llm / total, 1) if total else 0,
        "C_HITL_share_pct": round(100 * total_hitl / total, 1) if total else 0,
    }


# ---------------------------------------------------------------------------
# Monte Carlo cost distribution. (Improvement #2)
# ---------------------------------------------------------------------------

def acem_cost_monte_carlo(groups, alpha_spec, price_in_per_m, price_out_per_m,
                           reviewer_rate, infra_cost=0.0, context_model="linear",
                           context_cap=None, n_samples=2000, seed=None,
                           detail=False):
    """detail=True (Finding #6, docs/reviews/2026-08-04-improve-this.md,
    opt-in per user decision) additionally reports per-group and per-track
    C_LLM/C_HITL percentiles alongside the aggregate totals. Off by default
    to keep ordinary output small — pass detail=True when you need a
    distributional breakdown by group or track, not just in aggregate."""
    rng = random.Random(seed)
    totals, llm_totals, hitl_totals = [], [], []
    group_llm = {g["name"]: [] for g in groups} if detail else None
    group_hitl = {g["name"]: [] for g in groups} if detail else None
    track_subtotal = {} if detail else None

    for _ in range(n_samples):
        total_llm = 0.0
        total_hitl = 0.0
        sample_track_subtotal = {} if detail else None
        for g in groups:
            pos = g.get("position_factor", 0.5)
            rejection_rate = _sample(g["rejection_rate"], pos, rng)
            retries = _sample(g["retries_per_rejection"], pos, rng)
            # Resolve alpha at this group's own position, matching
            # acem_cost's per-group resolution (see Finding #4,
            # docs/reviews/2026-08-04-improve-this.md) — a non-stationary
            # alpha must vary by pipeline position the same way in both
            # the point-estimate and Monte Carlo paths.
            alpha = _sample(alpha_spec, pos, rng)

            rf = 1 + (rejection_rate * retries)
            cf = context_factor(alpha, pos, model=context_model, cap=context_cap)

            in_tokens = g["base_in"] * g["count"] * rf * cf
            out_tokens = g["base_out"] * g["count"] * rf * cf
            c_llm = (in_tokens * price_in_per_m / 1_000_000) + \
                    (out_tokens * price_out_per_m / 1_000_000)
            c_review = g["count"] * g["review_checkpoints_per_unit"] * \
                g["review_hours"] * reviewer_rate
            c_rework = g["count"] * rejection_rate * \
                g["rework_hours"] * reviewer_rate
            c_hitl = c_review + c_rework

            total_llm += c_llm
            total_hitl += c_hitl

            if detail:
                group_llm[g["name"]].append(c_llm)
                group_hitl[g["name"]].append(c_hitl)
                track = g.get("track", "main")
                sample_track_subtotal[track] = sample_track_subtotal.get(track, 0.0) + c_llm + c_hitl

        totals.append(total_llm + total_hitl + infra_cost)
        llm_totals.append(total_llm)
        hitl_totals.append(total_hitl)
        if detail:
            for track, subtotal in sample_track_subtotal.items():
                track_subtotal.setdefault(track, []).append(subtotal)

    def pctl(data, p):
        s = sorted(data)
        idx = min(len(s) - 1, max(0, round(p / 100 * (len(s) - 1))))
        return round(s[idx], 2)

    def pctl_summary(data):
        return {"p10": pctl(data, 10), "p50": pctl(data, 50), "p90": pctl(data, 90)}

    result = {
        "n_samples": n_samples,
        "Total_Cost": {
            "p10": pctl(totals, 10), "p50": pctl(totals, 50), "p90": pctl(totals, 90),
            "mean": round(statistics.mean(totals), 2),
            "stdev": round(statistics.pstdev(totals), 2),
        },
        "C_LLM_total": {
            "p10": pctl(llm_totals, 10), "p50": pctl(llm_totals, 50), "p90": pctl(llm_totals, 90),
        },
        "C_HITL_total": {
            "p10": pctl(hitl_totals, 10), "p50": pctl(hitl_totals, 50), "p90": pctl(hitl_totals, 90),
        },
    }

    if detail:
        result["groups"] = {
            name: {"C_LLM": pctl_summary(group_llm[name]), "C_HITL": pctl_summary(group_hitl[name])}
            for name in group_llm
        }
        result["tracks"] = {
            track: {"subtotal": pctl_summary(samples)}
            for track, samples in track_subtotal.items()
        }

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ACEM cost calculator")
    parser.add_argument("input", help="path to input JSON (see references/)")
    parser.add_argument("--montecarlo", type=int, metavar="N",
                         help="run a Monte Carlo simulation with N samples instead of a point estimate")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for --montecarlo (reproducibility)")
    parser.add_argument("--breakdown", action="store_true",
                         help="with --montecarlo, also report per-group and per-track cost percentiles "
                              "(off by default; aggregate-only output is smaller)")
    parser.add_argument("--calibration-log", metavar="PATH",
                         help="check a calibration log for stale/underpowered constants and print warnings")
    parser.add_argument("--context-model", choices=["linear", "sublinear", "capped"], default=None,
                         help="override context growth model (default: from input JSON, else 'linear')")
    args = parser.parse_args()

    with open(args.input) as f:
        cfg = json.load(f)

    context_model = args.context_model or cfg.get("context_model", "linear")
    context_cap = cfg.get("context_cap")

    calibration_warnings = None
    if args.calibration_log:
        calibration_warnings = check_calibration_log(args.calibration_log)
        if calibration_warnings:
            print("Calibration warnings:", file=sys.stderr)
            for w in calibration_warnings:
                print(f"  - {w}", file=sys.stderr)
        else:
            print("Calibration log: all constants within freshness/sample-size thresholds.", file=sys.stderr)

    if args.montecarlo:
        out = acem_cost_monte_carlo(
            cfg["groups"], cfg["alpha"], cfg["price_in_per_m"], cfg["price_out_per_m"],
            cfg["reviewer_rate"], cfg.get("infra_cost", 0.0),
            context_model=context_model, context_cap=context_cap,
            n_samples=args.montecarlo, seed=args.seed, detail=args.breakdown,
        )
    else:
        out = acem_cost(
            cfg["groups"], cfg["alpha"], cfg["price_in_per_m"], cfg["price_out_per_m"],
            cfg["reviewer_rate"], cfg.get("infra_cost", 0.0),
            context_model=context_model, context_cap=context_cap,
        )

    if calibration_warnings is not None:
        out["calibration_warnings"] = calibration_warnings

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

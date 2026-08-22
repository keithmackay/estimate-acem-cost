#!/usr/bin/env python3
"""Tests for acem_calculate.py.

These are regression/characterization tests for already-existing,
manually-verified behavior (see docs/reviews/2026-08-04-improve-this.md,
Finding #2) rather than tests written ahead of new feature development.
The `acem_cost`/`acem_cost_monte_carlo` regression cases lock in numbers
that were hand-verified against the paper's Table 5/6 worked examples and
this repo's example_input.json during development.
"""
import datetime
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import acem_calculate as acem  # noqa: E402


class TestResolveAndSample(unittest.TestCase):
    def test_resolve_constant(self):
        self.assertEqual(acem._resolve(5, 0.5), 5.0)

    def test_resolve_start_end_interpolates_by_position(self):
        self.assertAlmostEqual(acem._resolve({"start": 0.0, "end": 1.0}, 0.25), 0.25)
        self.assertAlmostEqual(acem._resolve({"start": 0.2, "end": 0.6}, 0.0), 0.2)
        self.assertAlmostEqual(acem._resolve({"start": 0.2, "end": 0.6}, 1.0), 0.6)

    def test_resolve_distribution_uses_mode_as_point_estimate(self):
        self.assertEqual(acem._resolve({"low": 1, "mode": 1.5, "high": 2}, 0.5), 1.5)

    def test_resolve_unrecognized_spec_raises(self):
        with self.assertRaises(ValueError):
            acem._resolve({"nonsense": 1}, 0.5)

    def test_sample_constant_returns_constant(self):
        rng = __import__("random").Random(42)
        self.assertEqual(acem._sample(3.0, 0.5, rng), 3.0)

    def test_sample_distribution_stays_within_bounds(self):
        rng = __import__("random").Random(42)
        for _ in range(500):
            v = acem._sample({"low": 1, "mode": 1.5, "high": 2}, 0.5, rng)
            self.assertGreaterEqual(v, 1)
            self.assertLessEqual(v, 2)


class TestContextFactor(unittest.TestCase):
    def test_linear(self):
        self.assertAlmostEqual(acem.context_factor(0.4, 0.5, model="linear"), 1.2)

    def test_sublinear_less_than_linear_for_early_position(self):
        # sqrt(pos) >= pos for pos in [0, 1], so sublinear CF should be >= linear CF
        linear = acem.context_factor(0.4, 0.25, model="linear")
        sublinear = acem.context_factor(0.4, 0.25, model="sublinear")
        self.assertGreater(sublinear, linear)

    def test_capped_respects_explicit_cap(self):
        # alpha * position would be 0.4*1.0 = 0.4, but cap=0.1 should limit it
        self.assertAlmostEqual(acem.context_factor(0.4, 1.0, model="capped", cap=0.1), 1.1)

    def test_capped_defaults_ceiling_to_alpha_when_no_cap_given(self):
        # alpha * position = 0.4 * 2.0 = 0.8, ceiling defaults to alpha (0.4)
        self.assertAlmostEqual(acem.context_factor(0.4, 2.0, model="capped", cap=None), 1.4)

    def test_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            acem.context_factor(0.4, 0.5, model="quadratic")


class TestConfidenceAndStaleness(unittest.TestCase):
    def test_confidence_label_boundaries(self):
        self.assertEqual(acem.confidence_label(None), "cold-start (uncalibrated default)")
        self.assertEqual(acem.confidence_label(2), "cold-start (uncalibrated default)")
        self.assertEqual(acem.confidence_label(3), "partial (small pilot sample)")
        self.assertEqual(acem.confidence_label(9), "partial (small pilot sample)")
        self.assertEqual(acem.confidence_label(10), "calibrated")

    def test_staleness_days_none_when_no_date(self):
        self.assertIsNone(acem.staleness_days(None))

    def test_staleness_days_computes_delta(self):
        today = datetime.date(2026, 8, 4)
        self.assertEqual(acem.staleness_days("2026-06-01", today=today), 64)


class TestCheckCalibrationLog(unittest.TestCase):
    def _write_log(self, constants):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump({"constants": constants}, f)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_healthy_entry_produces_no_warnings(self):
        today = datetime.date(2026, 8, 4)
        calibrated_date = (today - datetime.timedelta(days=10)).isoformat()
        path = self._write_log([{
            "name": "alpha", "sample_size": 12, "calibrated_date": calibrated_date,
            "agent_version": "v1", "current_agent_version": "v1",
        }])
        self.assertEqual(acem.check_calibration_log(path), [])

    def test_underpowered_sample_flagged(self):
        path = self._write_log([{"name": "beta", "sample_size": 2, "calibrated_date": None}])
        warnings = acem.check_calibration_log(path)
        self.assertEqual(len(warnings), 1)
        self.assertIn("only 2 pilot samples", warnings[0])

    def test_stale_date_flagged(self):
        path = self._write_log([{
            "name": "beta", "sample_size": 12, "calibrated_date": "2026-01-01",
        }])
        warnings = acem.check_calibration_log(path, max_age_days=90)
        self.assertEqual(len(warnings), 1)
        self.assertIn("due for recalibration", warnings[0])

    def test_agent_version_mismatch_flagged(self):
        path = self._write_log([{
            "name": "beta", "sample_size": 12, "calibrated_date": None,
            "agent_version": "v1", "current_agent_version": "v2",
        }])
        warnings = acem.check_calibration_log(path)
        self.assertEqual(len(warnings), 1)
        self.assertIn("recalibrate", warnings[0])

    def test_multiple_problems_produce_multiple_warnings(self):
        path = self._write_log([{
            "name": "beta", "sample_size": 1, "calibrated_date": "2020-01-01",
            "agent_version": "v1", "current_agent_version": "v2",
        }])
        warnings = acem.check_calibration_log(path, max_age_days=90)
        self.assertEqual(len(warnings), 3)


class TestAcemCostRegression(unittest.TestCase):
    """Locks in known-good output for references/example_input.json, hand
    verified against the paper's Table 5/6 worked-example methodology
    during development."""

    def setUp(self):
        input_path = os.path.join(
            os.path.dirname(__file__), "..", "references", "example_input.json")
        with open(input_path) as f:
            self.cfg = json.load(f)

    def test_known_good_totals(self):
        out = acem.acem_cost(
            self.cfg["groups"], self.cfg["alpha"],
            self.cfg["price_in_per_m"], self.cfg["price_out_per_m"],
            self.cfg["reviewer_rate"], self.cfg.get("infra_cost", 0.0),
        )
        self.assertEqual(out["C_LLM_total"], 15.87)
        self.assertEqual(out["C_HITL_total"], 3148.12)
        self.assertEqual(out["C_Infra"], 20)
        self.assertEqual(out["Total_Cost"], 3184.0)

    def test_group_and_track_breakdown_present(self):
        out = acem.acem_cost(
            self.cfg["groups"], self.cfg["alpha"],
            self.cfg["price_in_per_m"], self.cfg["price_out_per_m"],
            self.cfg["reviewer_rate"], self.cfg.get("infra_cost", 0.0),
        )
        self.assertEqual(len(out["groups"]), len(self.cfg["groups"]))
        self.assertIn("main", out["tracks"])
        # Independently-rounded C_LLM_total/C_HITL_total vs. the track
        # subtotal (rounded once, from unrounded parts) can differ by a
        # cent due to rounding order — not a bug, just display-level
        # rounding. Assert they're within a cent, not bit-identical.
        self.assertAlmostEqual(
            out["tracks"]["main"]["subtotal"],
            out["C_LLM_total"] + out["C_HITL_total"], delta=0.015)

    def test_confidence_label_defaults_to_cold_start(self):
        out = acem.acem_cost(
            self.cfg["groups"], self.cfg["alpha"],
            self.cfg["price_in_per_m"], self.cfg["price_out_per_m"],
            self.cfg["reviewer_rate"], self.cfg.get("infra_cost", 0.0),
        )
        for g in out["groups"]:
            self.assertEqual(g["confidence"], "cold-start (uncalibrated default)")


class TestAcemCostMonteCarlo(unittest.TestCase):
    def setUp(self):
        input_path = os.path.join(
            os.path.dirname(__file__), "..", "references", "example_input.json")
        with open(input_path) as f:
            self.cfg = json.load(f)

    def test_percentiles_are_ordered(self):
        out = acem.acem_cost_monte_carlo(
            self.cfg["groups"], self.cfg["alpha"],
            self.cfg["price_in_per_m"], self.cfg["price_out_per_m"],
            self.cfg["reviewer_rate"], self.cfg.get("infra_cost", 0.0),
            n_samples=500, seed=42,
        )
        for key in ("Total_Cost", "C_LLM_total", "C_HITL_total"):
            self.assertLessEqual(out[key]["p10"], out[key]["p50"])
            self.assertLessEqual(out[key]["p50"], out[key]["p90"])

    def test_deterministic_input_collapses_distribution(self):
        # example_input.json has no {low,mode,high} distributions, so every
        # sample should be identical and p10 == p50 == p90.
        out = acem.acem_cost_monte_carlo(
            self.cfg["groups"], self.cfg["alpha"],
            self.cfg["price_in_per_m"], self.cfg["price_out_per_m"],
            self.cfg["reviewer_rate"], self.cfg.get("infra_cost", 0.0),
            n_samples=200, seed=1,
        )
        self.assertEqual(out["Total_Cost"]["p10"], out["Total_Cost"]["p90"])
        self.assertEqual(out["Total_Cost"]["p50"], 3184.0)

    def test_non_stationary_alpha_resolved_per_group_like_point_estimate(self):
        # Finding #4 (docs/reviews/2026-08-04-improve-this.md): acem_cost
        # resolves a non-stationary alpha ({start,end}) at *each group's own*
        # position_factor. acem_cost_monte_carlo must do the same, not
        # resolve alpha once at a hardcoded position. With no {low,mode,high}
        # distributions anywhere, MC of a deterministic input should
        # collapse to exactly the point-estimate Total_Cost — this is the
        # same invariant as test_deterministic_input_collapses_distribution,
        # applied to a case with two groups at very different pipeline
        # positions, which is what actually exposes the bug.
        groups = [
            {
                "name": "early", "base_in": 10000, "base_out": 3000, "count": 10,
                "rejection_rate": 0.2, "retries_per_rejection": 1.5,
                "review_checkpoints_per_unit": 1, "review_hours": 0.2,
                "rework_hours": 0.4, "position_factor": 0.0,
            },
            {
                "name": "late", "base_in": 10000, "base_out": 3000, "count": 10,
                "rejection_rate": 0.2, "retries_per_rejection": 1.5,
                "review_checkpoints_per_unit": 1, "review_hours": 0.2,
                "rework_hours": 0.4, "position_factor": 1.0,
            },
        ]
        alpha_spec = {"start": 0.0, "end": 1.0}
        point = acem.acem_cost(groups, alpha_spec, 2.0, 10.0, 75)
        mc = acem.acem_cost_monte_carlo(groups, alpha_spec, 2.0, 10.0, 75,
                                         n_samples=50, seed=3)
        self.assertEqual(mc["Total_Cost"]["p10"], mc["Total_Cost"]["p90"])
        self.assertEqual(mc["Total_Cost"]["p50"], point["Total_Cost"])

    def test_seed_reproducibility(self):
        out1 = acem.acem_cost_monte_carlo(
            self.cfg["groups"], self.cfg["alpha"],
            self.cfg["price_in_per_m"], self.cfg["price_out_per_m"],
            self.cfg["reviewer_rate"], self.cfg.get("infra_cost", 0.0),
            n_samples=100, seed=7,
        )
        out2 = acem.acem_cost_monte_carlo(
            self.cfg["groups"], self.cfg["alpha"],
            self.cfg["price_in_per_m"], self.cfg["price_out_per_m"],
            self.cfg["reviewer_rate"], self.cfg.get("infra_cost", 0.0),
            n_samples=100, seed=7,
        )
        self.assertEqual(out1, out2)

    def test_detail_false_by_default_omits_group_and_track_breakdown(self):
        # Finding #6 (docs/reviews/2026-08-04-improve-this.md): opt-in only,
        # per user decision, so default output stays aggregate-only.
        out = acem.acem_cost_monte_carlo(
            self.cfg["groups"], self.cfg["alpha"],
            self.cfg["price_in_per_m"], self.cfg["price_out_per_m"],
            self.cfg["reviewer_rate"], self.cfg.get("infra_cost", 0.0),
            n_samples=50, seed=1,
        )
        self.assertNotIn("groups", out)
        self.assertNotIn("tracks", out)

    def test_detail_true_reports_per_group_and_per_track_percentiles(self):
        out = acem.acem_cost_monte_carlo(
            self.cfg["groups"], self.cfg["alpha"],
            self.cfg["price_in_per_m"], self.cfg["price_out_per_m"],
            self.cfg["reviewer_rate"], self.cfg.get("infra_cost", 0.0),
            n_samples=50, seed=1, detail=True,
        )
        group_names = {g["name"] for g in self.cfg["groups"]}
        self.assertEqual(set(out["groups"].keys()), group_names)
        for name in group_names:
            for key in ("C_LLM", "C_HITL"):
                self.assertIn("p10", out["groups"][name][key])
                self.assertIn("p50", out["groups"][name][key])
                self.assertIn("p90", out["groups"][name][key])
        self.assertEqual(set(out["tracks"].keys()), {"main"})
        self.assertIn("p50", out["tracks"]["main"]["subtotal"])

    def test_detail_true_aggregate_totals_match_detail_false(self):
        # Turning on detail must not change the aggregate numbers.
        kwargs = dict(
            groups=self.cfg["groups"], alpha_spec=self.cfg["alpha"],
            price_in_per_m=self.cfg["price_in_per_m"],
            price_out_per_m=self.cfg["price_out_per_m"],
            reviewer_rate=self.cfg["reviewer_rate"],
            infra_cost=self.cfg.get("infra_cost", 0.0),
            n_samples=50, seed=9,
        )
        without_detail = acem.acem_cost_monte_carlo(**kwargs)
        with_detail = acem.acem_cost_monte_carlo(**kwargs, detail=True)
        self.assertEqual(without_detail["Total_Cost"], with_detail["Total_Cost"])
        self.assertEqual(without_detail["C_LLM_total"], with_detail["C_LLM_total"])
        self.assertEqual(without_detail["C_HITL_total"], with_detail["C_HITL_total"])


class TestMainCalibrationWarningsInOutput(unittest.TestCase):
    """Finding #9 (docs/reviews/2026-08-04-improve-this.md): calibration
    warnings should be embedded in the JSON output (calibration_warnings),
    not only printed to stderr, so downstream consumers of the JSON don't
    lose the signal."""

    def _write_log(self, constants):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump({"constants": constants}, f)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def _write_input(self):
        input_path = os.path.join(
            os.path.dirname(__file__), "..", "references", "example_input.json")
        with open(input_path) as f:
            cfg = json.load(f)
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(cfg, f)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_output_carries_calibration_warnings_list(self):
        import subprocess
        log_path = self._write_log([{"name": "beta", "sample_size": 1, "calibrated_date": None}])
        input_path = self._write_input()
        script = os.path.join(os.path.dirname(__file__), "..", "acem_calculate.py")
        result = subprocess.run(
            [sys.executable, script, input_path, "--calibration-log", log_path],
            capture_output=True, text=True, check=True)
        out = json.loads(result.stdout)
        self.assertIn("calibration_warnings", out)
        self.assertEqual(len(out["calibration_warnings"]), 1)
        self.assertIn("only 1 pilot samples", out["calibration_warnings"][0])

    def test_output_calibration_warnings_empty_when_healthy(self):
        import subprocess
        today = datetime.date(2026, 8, 4).isoformat()
        log_path = self._write_log([{
            "name": "alpha", "sample_size": 12, "calibrated_date": today,
        }])
        input_path = self._write_input()
        script = os.path.join(os.path.dirname(__file__), "..", "acem_calculate.py")
        result = subprocess.run(
            [sys.executable, script, input_path, "--calibration-log", log_path],
            capture_output=True, text=True, check=True)
        out = json.loads(result.stdout)
        self.assertEqual(out["calibration_warnings"], [])

    def test_output_omits_calibration_warnings_when_no_log_passed(self):
        import subprocess
        input_path = self._write_input()
        script = os.path.join(os.path.dirname(__file__), "..", "acem_calculate.py")
        result = subprocess.run(
            [sys.executable, script, input_path],
            capture_output=True, text=True, check=True)
        out = json.loads(result.stdout)
        self.assertNotIn("calibration_warnings", out)


if __name__ == "__main__":
    unittest.main()

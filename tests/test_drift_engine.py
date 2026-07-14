"""
Tests for app/core/drift_engine.py

These are split into two groups:

1. Pure-logic unit tests (FairnessMonitor, _make_decision, _calculate_weighted_score,
   _get_enhanced_leaderboard) - fast, no external dependencies, no mocking needed.
   These test YOUR business logic, which is the part most likely to have bugs.

2. One integration test for run_analysis() that exercises the real evidently Report
   against small synthetic dataframes. This is slower and is marked accordingly -
   it's the test that would have caught the routes.py target_col issue you hit earlier.

Run with:  pytest tests/test_drift_engine.py -v
Run only fast tests:  pytest tests/test_drift_engine.py -v -m "not slow"
"""
import numpy as np
import pandas as pd
import pytest

from app.core.drift_engine import DriftAnalyzer, FairnessMonitor, FEATURE_CONFIG


# ---------------------------------------------------------------------------
# FairnessMonitor.check_bias
# ---------------------------------------------------------------------------

class TestFairnessMonitor:
    def setup_method(self):
        self.monitor = FairnessMonitor()

    def test_no_bias_when_groups_have_similar_positive_rates(self):
        # Both groups have ~50% positive rate -> disparate impact ~1.0, no issue
        n = 100
        df = pd.DataFrame({
            "sex": ["Male"] * n + ["Female"] * n,
            "class": (([">50K"] * 50 + ["<=50K"] * 50) * 2),
        })
        issues = self.monitor.check_bias(df, "sex", "class")
        assert issues == []

    def test_flags_disparate_impact_below_0_8(self):
        # Male group: 60/100 positive. Female group: 10/100 positive.
        # base_rate = 70/200 = 0.35. Female rate = 0.10 -> disparate impact = 0.10/0.35 = 0.286 < 0.8
        male = pd.DataFrame({"sex": ["Male"] * 100, "class": [">50K"] * 60 + ["<=50K"] * 40})
        female = pd.DataFrame({"sex": ["Female"] * 100, "class": [">50K"] * 10 + ["<=50K"] * 90})
        df = pd.concat([male, female], ignore_index=True)

        issues = self.monitor.check_bias(df, "sex", "class")

        assert len(issues) == 1
        assert issues[0]["group"] == "Female"
        assert float(issues[0]["disparity"]) < 0.8

    def test_ignores_groups_below_50_row_minimum(self):
        # Female group only has 10 rows -> should be skipped regardless of disparity
        male = pd.DataFrame({"sex": ["Male"] * 100, "class": [">50K"] * 60 + ["<=50K"] * 40})
        female = pd.DataFrame({"sex": ["Female"] * 10, "class": [">50K"] * 1 + ["<=50K"] * 9})
        df = pd.concat([male, female], ignore_index=True)

        issues = self.monitor.check_bias(df, "sex", "class")
        assert issues == []

    def test_missing_columns_returns_empty_list_not_exception(self):
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        assert self.monitor.check_bias(df, "sex", "class") == []
        assert self.monitor.check_bias(df, "nonexistent", "also_nonexistent") == []

    def test_zero_base_rate_returns_empty_list(self):
        # Everyone is negative class -> base_rate == 0 -> must not divide by zero
        n = 60
        df = pd.DataFrame({"sex": ["Male"] * n, "class": ["<=50K"] * n})
        assert self.monitor.check_bias(df, "sex", "class") == []


# ---------------------------------------------------------------------------
# DriftAnalyzer._calculate_weighted_score
# ---------------------------------------------------------------------------

class TestCalculateWeightedScore:
    def setup_method(self):
        # target_col=None avoids constructing a ColumnDriftMetric we don't need for these tests
        self.analyzer = DriftAnalyzer.__new__(DriftAnalyzer)  # bypass __init__ (no evidently needed)

    def test_empty_leaderboard_returns_zero(self):
        assert self.analyzer._calculate_weighted_score([]) == 0

    def test_no_detected_drift_returns_zero(self):
        leaderboard = [
            {"feature": "age", "score": 0.9, "detected": False, "weight": 2.5},
            {"feature": "sex", "score": 0.9, "detected": False, "weight": 5.0},
        ]
        assert self.analyzer._calculate_weighted_score(leaderboard) == 0

    def test_score_is_capped_at_100(self):
        # Real evidently drift scores are ~0-1, so a score of 10 is artificial -
        # this just proves the min(100, ...) cap actually engages when the math
        # would otherwise overshoot.
        leaderboard = [
            {"feature": "class", "score": 10.0, "detected": True, "weight": 10.0},
        ]
        result = self.analyzer._calculate_weighted_score(leaderboard)
        assert result == 100

    def test_weighted_average_respects_feature_weights(self):
        # One high-weight, fully-drifted feature should dominate the score
        leaderboard = [
            {"feature": "class", "score": 1.0, "detected": True, "weight": 10.0},
            {"feature": "fnlwgt", "score": 1.0, "detected": True, "weight": 0.1},
        ]
        result = self.analyzer._calculate_weighted_score(leaderboard)
        expected = min(100, ((1.0 * 10.0 + 1.0 * 0.1) / 10.1) * 25)
        assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# DriftAnalyzer._make_decision
# ---------------------------------------------------------------------------

class TestMakeDecision:
    def setup_method(self):
        self.analyzer = DriftAnalyzer.__new__(DriftAnalyzer)
        self.analyzer.registry = None

    def test_cooldown_short_circuits_everything(self):
        decision = self.analyzer._make_decision(
            weighted_score=99, drift_share=0.9, target_drift=0.9, has_bias=True,
            in_cooldown=True, version="v1.0.0"
        )
        assert decision["action"] == "COOLDOWN"

    def test_bias_blocks_deployment_even_with_low_drift(self):
        decision = self.analyzer._make_decision(
            weighted_score=0, drift_share=0, target_drift=0, has_bias=True,
            in_cooldown=False, version="v1.0.0"
        )
        assert decision["action"] == "BLOCK DEPLOYMENT"

    def test_target_drift_detected_triggers_rollback(self):
        # target_drift score itself (0.15) is irrelevant now - drift_detected is
        # the actual trigger, since score direction depends on which stattest
        # evidently picked for this column.
        decision = self.analyzer._make_decision(
            weighted_score=0, drift_share=0, target_drift=0.15, has_bias=False,
            in_cooldown=False, version="v1.0.0", target_drift_available=True,
            target_drift_detected=True,
        )
        assert decision["action"] == "EMERGENCY ROLLBACK"
        assert decision["rollback_executed"] is False  # no registry attached

    def test_target_drift_not_detected_does_not_trigger_rollback(self):
        decision = self.analyzer._make_decision(
            weighted_score=0, drift_share=0, target_drift=0.99, has_bias=False,
            in_cooldown=False, version="v1.0.0", target_drift_available=True,
            target_drift_detected=False,
        )
        assert decision["action"] != "EMERGENCY ROLLBACK"

    def test_target_drift_ignored_when_unavailable(self):
        # Even if drift_detected=True, target_drift_available=False means there
        # was no target column in the uploaded data at all, so it must NOT fire.
        decision = self.analyzer._make_decision(
            weighted_score=0, drift_share=0, target_drift=0.15, has_bias=False,
            in_cooldown=False, version="v1.0.0", target_drift_available=False,
            target_drift_detected=True,
        )
        assert decision["action"] != "EMERGENCY ROLLBACK"

    def test_weighted_score_above_60_triggers_full_retrain(self):
        decision = self.analyzer._make_decision(
            weighted_score=75, drift_share=0.5, target_drift=0.05, has_bias=False,
            in_cooldown=False, version="v1.0.0"
        )
        assert decision["action"] == "FULL RETRAINING"

    def test_weighted_score_between_20_and_60_triggers_fine_tune(self):
        decision = self.analyzer._make_decision(
            weighted_score=30, drift_share=0.3, target_drift=0.05, has_bias=False,
            in_cooldown=False, version="v1.0.0"
        )
        assert decision["action"] == "TRIGGER FINE-TUNING"

    def test_low_score_means_no_action(self):
        decision = self.analyzer._make_decision(
            weighted_score=5, drift_share=0.05, target_drift=0.01, has_bias=False,
            in_cooldown=False, version="v1.0.0"
        )
        assert decision["action"] == "NO ACTION"
        assert decision["status"] == "HEALTHY"

    def test_rollback_calls_registry_when_attached(self):
        calls = {}

        class FakeRegistry:
            def execute_rollback(self, reason=None):
                calls["reason"] = reason
                return {"rolled_back_to": "v0.9.0"}

        self.analyzer.registry = FakeRegistry()
        decision = self.analyzer._make_decision(
            weighted_score=0, drift_share=0, target_drift=0.2, has_bias=False,
            in_cooldown=False, version="v1.0.0", target_drift_available=True,
            target_drift_detected=True,
        )
        assert decision["rollback_executed"] is True
        assert "0.2" in calls["reason"]


# ---------------------------------------------------------------------------
# DriftAnalyzer._get_enhanced_leaderboard
# ---------------------------------------------------------------------------

class TestEnhancedLeaderboard:
    def setup_method(self):
        self.analyzer = DriftAnalyzer.__new__(DriftAnalyzer)

    def _make_json_result(self, drift_by_columns):
        return {
            "metrics": [
                {"metric": "DataDriftTable", "result": {"drift_by_columns": drift_by_columns}}
            ]
        }

    def test_applies_known_feature_config(self):
        json_result = self._make_json_result({
            "age": {"drift_score": 0.5, "drift_detected": True},
        })
        lb = self.analyzer._get_enhanced_leaderboard(json_result)
        assert lb[0]["feature"] == "age"
        assert lb[0]["weight"] == FEATURE_CONFIG["age"]["weight"]
        assert lb[0]["impact_tag"] == "HIGH"

    def test_unknown_feature_gets_default_config(self):
        json_result = self._make_json_result({
            "some_unmapped_col": {"drift_score": 0.2, "drift_detected": False},
        })
        lb = self.analyzer._get_enhanced_leaderboard(json_result)
        assert lb[0]["weight"] == 1.0
        assert lb[0]["impact_tag"] == "NORMAL"

    def test_sorted_by_score_times_weight_descending(self):
        json_result = self._make_json_result({
            "fnlwgt": {"drift_score": 0.9, "drift_detected": True},   # weight 0.1 -> 0.09
            "class": {"drift_score": 0.1, "drift_detected": True},    # weight 10.0 -> 1.0
        })
        lb = self.analyzer._get_enhanced_leaderboard(json_result)
        assert lb[0]["feature"] == "class"

    def test_caps_at_8_features(self):
        cols = {f"col_{i}": {"drift_score": 0.1 * i, "drift_detected": True} for i in range(15)}
        json_result = self._make_json_result(cols)
        lb = self.analyzer._get_enhanced_leaderboard(json_result)
        assert len(lb) == 8

    def test_malformed_json_returns_empty_list_not_exception(self):
        assert self.analyzer._get_enhanced_leaderboard({"metrics": []}) == []


# ---------------------------------------------------------------------------
# Integration test - real evidently Report against synthetic data
# ---------------------------------------------------------------------------

class FakeDB:
    """Minimal stand-in for DatabaseEngine, only implementing what run_analysis calls."""
    def __init__(self):
        self.logged = []

    def check_cooldown(self):
        return (False, None)

    def get_current_version(self):
        return "v1.0.0-test"

    def log_run(self, drift_share, weighted_score, revenue_risk, decision):
        self.logged.append((drift_share, weighted_score, revenue_risk, decision))


@pytest.mark.slow
class TestRunAnalysisIntegration:
    def _stable_dataframes(self, n=200, seed=1):
        rng = np.random.default_rng(seed)
        ref = pd.DataFrame({
            "age": rng.integers(20, 60, n),
            "capital-gain": rng.integers(0, 5000, n),
            "class": rng.choice([">50K", "<=50K"], n, p=[0.3, 0.7]),
        })
        # current drawn from the same distribution -> should show low/no drift
        curr = pd.DataFrame({
            "age": rng.integers(20, 60, n),
            "capital-gain": rng.integers(0, 5000, n),
            "class": rng.choice([">50K", "<=50K"], n, p=[0.3, 0.7]),
        })
        return ref, curr

    def _drifted_dataframes(self, n=200, seed=2):
        rng = np.random.default_rng(seed)
        ref = pd.DataFrame({
            "age": rng.integers(20, 40, n),          # reference skews younger
            "capital-gain": rng.integers(0, 1000, n),
            "class": rng.choice([">50K", "<=50K"], n, p=[0.2, 0.8]),
        })
        curr = pd.DataFrame({
            "age": rng.integers(50, 80, n),           # current skews much older -> drift
            "capital-gain": rng.integers(20000, 50000, n),
            "class": rng.choice([">50K", "<=50K"], n, p=[0.9, 0.1]),  # label shift
        })
        return ref, curr

    def test_run_analysis_on_stable_data_returns_expected_shape(self):
        ref, curr = self._stable_dataframes()
        db = FakeDB()
        analyzer = DriftAnalyzer(db_engine=db, registry=None, target_col="class")

        result = analyzer.run_analysis(ref, curr)

        for key in ("html_report", "meta", "financials", "model_health", "rigor", "automation", "leaderboard"):
            assert key in result
        assert result["meta"]["target_drift_tracked"] is True
        assert len(db.logged) == 1  # log_run should be called exactly once

    def test_run_analysis_detects_label_shift_and_recommends_rollback(self):
        """
        This replaces a previous test that documented a real bug: the automation
        layer used to check `target_drift > 0.1` on the raw score, which is
        backwards for p-value-style stat tests (the "class" column uses a Z-test,
        where a LOW p-value means drift WAS detected). That made this exact
        scenario - a severe, deliberate label shift (positive rate 0.2 -> 0.9) -
        silently report "NO ACTION" instead of escalating.

        Fixed in drift_engine.py by gating on the `drift_detected` boolean
        (evidently's own normalized verdict) instead of the raw score, which is
        correct regardless of which stattest family evidently selects for a
        given column's type.
        """
        ref, curr = self._drifted_dataframes()
        db = FakeDB()
        analyzer = DriftAnalyzer(db_engine=db, registry=None, target_col="class")

        result = analyzer.run_analysis(ref, curr)

        assert result["automation"]["action"] == "EMERGENCY ROLLBACK"
        assert result["model_health"]["reliability"] == "DEGRADED"

    def test_run_analysis_falls_back_gracefully_without_target_column(self):
        ref, curr = self._stable_dataframes()
        ref = ref.drop(columns=["class"])
        curr = curr.drop(columns=["class"])
        db = FakeDB()
        analyzer = DriftAnalyzer(db_engine=db, registry=None, target_col="class")

        result = analyzer.run_analysis(ref, curr)

        assert result["meta"]["target_drift_tracked"] is False
        assert result["automation"]["action"] != "EMERGENCY ROLLBACK"
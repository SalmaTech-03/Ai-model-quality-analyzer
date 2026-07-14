import pandas as pd
import json
import numpy as np
from datetime import datetime
from scipy.stats import ks_2samp

from evidently.report import Report
from evidently.metrics import DatasetDriftMetric, DataDriftTable, ColumnDriftMetric

FEATURE_CONFIG = {
    "age": {"weight": 2.5, "impact": "HIGH", "action": "Retrain (Demographic Shift)"},
    "capital-gain": {"weight": 2.0, "impact": "HIGH", "action": "Recalibrate Thresholds"},
    "class": {"weight": 10.0, "impact": "CRITICAL", "action": "URGENT: Label Shift"},
    "sex": {"weight": 5.0, "impact": "HIGH", "action": "Fairness Audit"},
    "race": {"weight": 5.0, "impact": "HIGH", "action": "Fairness Audit"},
    "fnlwgt": {"weight": 0.1, "impact": "LOW", "action": "Ignore (Sampling Noise)"},
    "education-num": {"weight": 1.5, "impact": "MEDIUM", "action": "Monitor Feature"}
}


class FairnessMonitor:
    def check_bias(self, df: pd.DataFrame, protected_col: str, target_col: str):
        if protected_col not in df.columns or target_col not in df.columns:
            return []

        try:
            df['y_bin'] = df[target_col].apply(lambda x: 1 if str(x).strip() in ['>50K', '1', 'yes'] else 0)
        except Exception:
            return []

        base_rate = df['y_bin'].mean()
        if base_rate == 0:
            return []

        issues = []
        groups = df.groupby(protected_col)['y_bin'].agg(['mean', 'count'])

        for group, stats in groups.iterrows():
            if stats['count'] < 50:
                continue

            group_rate = stats['mean']
            disparate_impact = group_rate / base_rate

            if disparate_impact < 0.8:
                issues.append({
                    "group": str(group),
                    "disparity": f"{disparate_impact:.2f}",
                    "details": f"Group positive rate is {disparate_impact*100:.1f}% of the average."
                })

        return issues


class DriftAnalyzer:
    def __init__(self, db_engine=None, registry=None, target_col: str = "class"):
        metrics = [DatasetDriftMetric(), DataDriftTable()]
        self.target_col = target_col
        if target_col:
            metrics.append(ColumnDriftMetric(column_name=target_col))
        self.report = Report(metrics=metrics)
        self.db = db_engine
        self.registry = registry
        self.fairness = FairnessMonitor()

    def run_analysis(self, ref_df: pd.DataFrame, curr_df: pd.DataFrame):
        in_cooldown, _ = self.db.check_cooldown() if self.db else (False, None)
        current_version = self.db.get_current_version() if self.db else "v1.0.0"

        has_target = self.target_col in ref_df.columns and self.target_col in curr_df.columns
        try:
            if not has_target:
                raise ValueError(f"target column '{self.target_col}' not present")
            self.report.run(reference_data=ref_df, current_data=curr_df)
            json_result = json.loads(self.report.json())
        except Exception:
            fallback = Report(metrics=[DatasetDriftMetric(), DataDriftTable()])
            fallback.run(reference_data=ref_df, current_data=curr_df)
            json_result = json.loads(fallback.json())
            has_target = False

        stat_significance = []
        for col in ref_df.select_dtypes(include=np.number).columns:
            try:
                stat, p_val = ks_2samp(ref_df[col], curr_df[col])
                if p_val < 0.05:
                    stat_significance.append({
                        "feature": col,
                        "p_value": float(f"{p_val:.4e}")
                    })
            except Exception:
                pass

        fairness_issues = []
        for p_col in ['sex', 'race', 'relationship']:
            issues = self.fairness.check_bias(curr_df, p_col, self.target_col)
            if issues:
                for i in issues:
                    i['feature'] = p_col
                fairness_issues.extend(issues)

        drift_metric = next(m for m in json_result['metrics'] if m['metric'] == 'DatasetDriftMetric')
        drift_share = drift_metric['result']['drift_share']

        target_drift = 0.0
        target_drift_detected = False
        target_stattest_name = None
        if has_target:
            try:
                tm = next(
                    m for m in json_result['metrics']
                    if m['metric'] == 'ColumnDriftMetric' and m['result']['column_name'] == self.target_col
                )
                target_drift = tm['result']['drift_score']
                # drift_detected is the correct signal to act on: evidently picks the
                # stattest per column (Z-test/p-value for categorical columns vs.
                # distance-based tests like PSI/Wasserstein for numeric columns), and
                # those two families point in OPPOSITE directions on drift_score
                # (low p-value = drift; high PSI/Wasserstein = drift). Comparing the
                # raw score against a fixed threshold silently breaks for whichever
                # family isn't the one the threshold was tuned for. drift_detected is
                # evidently's own already-normalized verdict, so it's safe to use
                # regardless of which stattest got selected.
                target_drift_detected = bool(tm['result'].get('drift_detected', False))
                target_stattest_name = tm['result'].get('stattest_name')
            except StopIteration:
                pass

        est_f1_drop = target_drift * 0.4
        # Reliability must also key off drift_detected, not just the raw score -
        # otherwise a p-value-style score of 0.0 (== "very drifted") gets read as
        # "no measurable impact" and reports STABLE for a model that just failed.
        reliability_status = "DEGRADED" if (target_drift_detected or est_f1_drop >= 0.05) else "STABLE"

        revenue_risk = len(curr_df) * 150 * ((drift_share * 0.1) + est_f1_drop)

        leaderboard = self._get_enhanced_leaderboard(json_result)
        weighted_score = self._calculate_weighted_score(leaderboard)

        decision = self._make_decision(
            weighted_score, drift_share, target_drift,
            len(fairness_issues) > 0, in_cooldown, current_version,
            target_drift_available=has_target,
            target_drift_detected=target_drift_detected,
        )

        if self.db and not in_cooldown:
            self.db.log_run(drift_share, weighted_score, revenue_risk, decision)

        return {
            "html_report": self.report.get_html(),
            "meta": {
                "version": current_version,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cooldown": in_cooldown,
                "target_drift_tracked": has_target,
                "target_stattest": target_stattest_name,
            },
            "financials": {
                "risk_amount": f"${int(revenue_risk):,}",
                "disclaimer": "*Risk = Vol * $150 (Avg Cost) * (0.1 * DriftShare + 0.4 * TargetDrift)"
            },
            "model_health": {
                "reliability": reliability_status,
                "est_f1_drop": f"-{est_f1_drop*100:.1f}%",
                "target_drift": f"{target_drift:.3f}"
            },
            "rigor": {
                "p_values": stat_significance,
                "fairness": fairness_issues
            },
            "automation": decision,
            "leaderboard": leaderboard
        }

    def _make_decision(self, weighted_score, drift_share, target_drift, has_bias,
                        in_cooldown, version, target_drift_available=True,
                        target_drift_detected=False):
        if in_cooldown:
            return {"action": "COOLDOWN", "status": "SKIPPED", "color": "#94a3b8",
                    "rule": "Run < 24h", "details": "Skipping to prevent flap.",
                    "pipeline": "Monitor", "strategy": "N/A"}

        if has_bias:
            return {"action": "BLOCK DEPLOYMENT", "status": "CRITICAL", "color": "#ff0055",
                    "rule": "Fairness Violation",
                    "details": "Disparate impact detected in protected groups.",
                    "pipeline": "Notify Legal/Compliance", "strategy": "Audit"}

        # Gate on drift_detected, not a raw-score threshold. evidently selects the
        # stattest per column, and score direction differs by test family (p-value
        # tests: low score = drift; distance tests like PSI/Wasserstein: high score
        # = drift). drift_detected is evidently's own normalized verdict, so it's
        # correct regardless of which family got picked for this column.
        if target_drift_available and target_drift_detected:
            rollback_log = None
            if self.registry:
                rollback_log = self.registry.execute_rollback(
                    reason=f"Target drift detected (score={target_drift:.3f})"
                )
            return {
                "action": "EMERGENCY ROLLBACK", "status": "CRITICAL", "color": "#ff0055",
                "rule": "HARD OVERRIDE: Label Shift",
                "details": "Model assumptions invalidated.",
                "pipeline": "Kill Traffic -> Rollback",
                "strategy": "Human Audit",
                "rollback_executed": rollback_log is not None,
                "rollback_detail": rollback_log,
            }

        if weighted_score > 60:
            return {"action": "FULL RETRAINING", "status": "CRITICAL", "color": "#ef4444",
                    "rule": "Weighted Risk > 60", "details": "High feature drift.",
                    "pipeline": "Airflow: Retrain_Full", "strategy": "Full History"}
        elif weighted_score > 20:
            return {"action": "TRIGGER FINE-TUNING", "status": "WARNING", "color": "#f59e0b",
                    "rule": "Weighted Risk > 20", "details": "Moderate degradation.",
                    "pipeline": "Step 1: Retrain -> Shadow", "strategy": "Recent Window"}

        return {"action": "NO ACTION", "status": "HEALTHY", "color": "#22c55e",
                "rule": "Nominal", "details": "Stable.", "pipeline": "Monitor", "strategy": "N/A"}

    def _get_enhanced_leaderboard(self, json_result):
        try:
            table = next(m for m in json_result['metrics'] if m['metric'] == 'DataDriftTable')
            drift_cols = table['result']['drift_by_columns']
            lb = []
            for feat, det in drift_cols.items():
                config = FEATURE_CONFIG.get(feat, {"weight": 1.0, "impact": "NORMAL", "action": "Monitor"})
                lb.append({
                    "feature": feat,
                    "score": det['drift_score'],
                    "detected": det['drift_detected'],
                    "weight": config['weight'],
                    "impact_tag": config['impact'],
                    "suggested_action": config['action']
                })
            return sorted(lb, key=lambda x: x['score'] * x['weight'], reverse=True)[:8]
        except Exception:
            return []

    def _calculate_weighted_score(self, leaderboard):
        total_w = 0
        score = 0
        for item in leaderboard:
            w = item['weight']
            total_w += w
            if item['detected']:
                score += (item['score'] * w)
        return min(100, (score / total_w) * 25) if total_w > 0 else 0
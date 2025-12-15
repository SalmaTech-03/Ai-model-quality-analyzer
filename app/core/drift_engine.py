import pandas as pd
import json
import numpy as np
from datetime import datetime
from scipy.stats import ks_2samp  # For Statistical Rigor (P-Values)

# Evidently Imports
from evidently.report import Report
from evidently.metrics import DatasetDriftMetric, DataDriftTable, ColumnDriftMetric

# --- ENTERPRISE KNOWLEDGE GRAPH ---
# Defines business importance and actions for specific features
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
    """
    The Auditor: Checks for Disparate Impact on protected groups.
    Metric: Disparate Impact Ratio (DIR) < 0.8 is the standard threshold.
    """
    def check_bias(self, df: pd.DataFrame, protected_col: str, target_col: str):
        if protected_col not in df.columns or target_col not in df.columns:
            return []

        # Convert target to binary (assuming >50K is the "Positive" outcome)
        try:
            # Flexible logic for different datasets
            df['y_bin'] = df[target_col].apply(lambda x: 1 if str(x).strip() in ['>50K', '1', 'yes'] else 0)
        except:
            return []

        base_rate = df['y_bin'].mean()
        if base_rate == 0: return []

        issues = []
        # Calculate positive rate for each group
        groups = df.groupby(protected_col)['y_bin'].agg(['mean', 'count'])
        
        for group, stats in groups.iterrows():
            if stats['count'] < 50: continue # Skip statistically insignificant sample sizes
            
            group_rate = stats['mean']
            disparate_impact = group_rate / base_rate
            
            # 4/5ths Rule (80%): If a group succeeds <80% as often as the average -> Bias
            if disparate_impact < 0.8:
                issues.append({
                    "group": str(group),
                    "disparity": f"{disparate_impact:.2f}",
                    "details": f"Group positive rate is {disparate_impact*100:.1f}% of the average."
                })
        
        return issues

class DriftAnalyzer:
    def __init__(self, db_engine=None):
        self.report = Report(metrics=[
            DatasetDriftMetric(),
            DataDriftTable(),
            ColumnDriftMetric(column_name="class") # Explicitly track Target Drift
        ])
        self.db = db_engine
        self.fairness = FairnessMonitor()

    def run_analysis(self, ref_df: pd.DataFrame, curr_df: pd.DataFrame):
        # 1. INIT & STATE CHECK
        in_cooldown, _ = self.db.check_cooldown() if self.db else (False, None)
        current_version = self.db.get_current_version() if self.db else "v1.0.0"

        # 2. RUN EVIDENTLY (The Math)
        try:
            self.report.run(reference_data=ref_df, current_data=curr_df)
            json_result = json.loads(self.report.json())
        except:
            # Fallback if 'class' column is missing
            fallback = Report(metrics=[DatasetDriftMetric(), DataDriftTable()])
            fallback.run(reference_data=ref_df, current_data=curr_df)
            json_result = json.loads(fallback.json())

        # 3. STATISTICAL RIGOR (P-Values)
        # Verify drift with Kolmogorov-Smirnov Test (Non-parametric)
        stat_significance = []
        for col in ref_df.select_dtypes(include=np.number).columns:
            try:
                stat, p_val = ks_2samp(ref_df[col], curr_df[col])
                if p_val < 0.05: # Statistically Significant Drift
                    stat_significance.append({
                        "feature": col,
                        "p_value": float(f"{p_val:.4e}")
                    })
            except: pass

        # 4. FAIRNESS AUDIT (The Ethics)
        fairness_issues = []
        for p_col in ['sex', 'race', 'relationship']:
            issues = self.fairness.check_bias(curr_df, p_col, 'class')
            if issues:
                for i in issues: i['feature'] = p_col
                fairness_issues.extend(issues)

        # 5. METRICS EXTRACTION
        drift_metric = next(m for m in json_result['metrics'] if m['metric'] == 'DatasetDriftMetric')
        drift_share = drift_metric['result']['drift_share']
        
        target_drift = 0.0
        try:
            tm = next(m for m in json_result['metrics'] if m['metric'] == 'ColumnDriftMetric' and m['result']['column_name'] == 'class')
            target_drift = tm['result']['drift_score']
        except: pass

        # 6. RISK & DECISION
        # Simulation: 0.1 target drift ~ 4% F1 Drop
        est_f1_drop = target_drift * 0.4
        reliability_status = "STABLE" if est_f1_drop < 0.05 else "DEGRADED"
        
        # Financial Risk Formula: Volume * Avg Cost ($150) * Est. Error Increase
        revenue_risk = len(curr_df) * 150 * ((drift_share * 0.1) + est_f1_drop)
        
        leaderboard = self._get_enhanced_leaderboard(json_result)
        weighted_score = self._calculate_weighted_score(leaderboard)
        
        decision = self._make_decision(weighted_score, drift_share, target_drift, len(fairness_issues) > 0, in_cooldown, current_version)

        # 7. LOGGING
        if self.db and not in_cooldown:
            self.db.log_run(drift_share, weighted_score, revenue_risk, decision)

        return {
            "html_report": self.report.get_html(),
            "meta": {
                "version": current_version,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cooldown": in_cooldown
            },
            "financials": {
                "risk_amount": f"${int(revenue_risk):,}",
                "disclaimer": "*Risk = Vol * $150 (Avg Cost) * Est. Error Rate"
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

    def _make_decision(self, weighted_score, drift_share, target_drift, has_bias, in_cooldown, version):
        """
        Deterministic Decision Gate.
        Priority: Cooldown -> Bias -> Target Drift -> Weighted Score.
        """
        # 1. COOLDOWN
        if in_cooldown:
            return {"action": "COOLDOWN", "status": "SKIPPED", "color": "#94a3b8", "rule": "Run < 24h", "details": "Skipping to prevent flap.", "pipeline": "Monitor", "strategy": "N/A"}

        # 2. PRIORITY: FAIRNESS VIOLATION
        if has_bias:
            return {"action": "BLOCK DEPLOYMENT", "status": "CRITICAL", "color": "#ff0055", "rule": "Fairness Violation", "details": "Disparate impact detected in protected groups.", "pipeline": "Notify Legal/Compliance", "strategy": "Audit"}

        # 3. PRIORITY: CIRCUIT BREAKER (Target Drift)
        if target_drift > 0.1:
            return {"action": "EMERGENCY ROLLBACK", "status": "CRITICAL", "color": "#ff0055", "rule": "⛔ HARD OVERRIDE: Label Shift", "details": "Model assumptions invalidated.", "pipeline": "Kill Traffic -> Rollback", "strategy": "Human Audit"}

        # 4. STANDARD LOGIC
        if weighted_score > 60:
            return {"action": "FULL RETRAINING", "status": "CRITICAL", "color": "#ef4444", "rule": "Weighted Risk > 60", "details": "High feature drift.", "pipeline": "Airflow: Retrain_Full", "strategy": "Full History"}
        elif weighted_score > 20:
            return {"action": "TRIGGER FINE-TUNING", "status": "WARNING", "color": "#f59e0b", "rule": "Weighted Risk > 20", "details": "Moderate degradation.", "pipeline": "Step 1: Retrain -> Shadow", "strategy": "Recent Window"}
        
        return {"action": "NO ACTION", "status": "HEALTHY", "color": "#22c55e", "rule": "Nominal", "details": "Stable.", "pipeline": "Monitor", "strategy": "N/A"}

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
        except: return []

    def _calculate_weighted_score(self, leaderboard):
        total_w = 0; score = 0
        for item in leaderboard:
            w = item['weight']; total_w += w
            if item['detected']: score += (item['score'] * w)
        return min(100, (score / total_w) * 25) if total_w > 0 else 0
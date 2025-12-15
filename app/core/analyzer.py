import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
from app.config import RISK_HIGH_THRESHOLD, RISK_MID_THRESHOLD

class DriftAnalyzer:
    """
    Core Logic for detecting Distribution Drift in Tabular Data.
    """
    def __init__(self):
        self.report = Report(metrics=[
            DataDriftPreset(),
            DataQualityPreset()
        ])

    def run_analysis(self, ref_df: pd.DataFrame, curr_df: pd.DataFrame) -> dict:
        """
        Runs Evidently, extracts metrics robustly, and calculates custom Risk Score.
        """
        # 1. Run the Mathematical Engine
        self.report.run(reference_data=ref_df, current_data=curr_df)
        result = self.report.as_dict()
        
        # 2. ROBUST EXTRACTION (The Fix)
        # We initialize defaults
        drift_share = 0
        drift_detected = False
        drift_by_columns = {}

        # We loop through ALL metrics to gather pieces of info
        for metric in result['metrics']:
            metric_result = metric['result']

            # Case A: Found the Summary Stats (DatasetDriftMetric)
            if 'drift_share' in metric_result:
                drift_share = metric_result['drift_share']
                drift_detected = metric_result['dataset_drift']

            # Case B: Found the Detailed Stats (DataDriftTable)
            if 'drift_by_columns' in metric_result:
                drift_by_columns = metric_result['drift_by_columns']

        # 3. GENERATE LEADERBOARD (Top 5 Drifting Features)
        leaderboard = []
        for feature, stats in drift_by_columns.items():
            leaderboard.append({
                "feature": feature,
                "score": stats['drift_score'],
                "method": stats['stattest_name'],
                "detected": stats['drift_detected']
            })
        
        # Sort descending
        leaderboard = sorted(leaderboard, key=lambda x: x['score'], reverse=True)[:5]

        # 4. CALCULATE CUSTOM RISK BADGE
        if drift_share > RISK_HIGH_THRESHOLD:
            risk_level = "HIGH"
            risk_color = "#ef4444" # Red
        elif drift_share > RISK_MID_THRESHOLD:
            risk_level = "MEDIUM"
            risk_color = "#f59e0b" # Orange
        else:
            risk_level = "LOW"
            risk_color = "#22c55e" # Green

        # 5. Return structured data
        return {
            "drift_detected": drift_detected,
            "drift_share": drift_share,
            "risk_level": risk_level,
            "risk_color": risk_color,
            "leaderboard": leaderboard,
            "html_report": self.report.get_html()
        }
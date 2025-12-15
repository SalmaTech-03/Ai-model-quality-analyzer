import pandas as pd
import numpy as np

class FairnessEngine:
    def __init__(self, protected_columns=["race", "sex", "relationship"]):
        self.protected_columns = protected_columns

    def run_fairness_scan(self, df: pd.DataFrame, target_col="class"):
        """
        Slices the dataset by protected groups and calculates prevalence/error rates.
        """
        issues = []
        metrics = {}
        
        # Ensure we have a binary target for calculation (assuming >50K is positive)
        # In a real scenario, this mapping comes from the Model Registry
        if target_col not in df.columns:
            return {"status": "SKIPPED", "reason": "No target column for fairness check"}

        df['target_binary'] = df[target_col].apply(lambda x: 1 if str(x).strip() in ['>50K', '1'] else 0)
        overall_rate = df['target_binary'].mean()

        for col in self.protected_columns:
            if col not in df.columns: continue
            
            # Calculate positive rate per group
            group_stats = df.groupby(col)['target_binary'].agg(['mean', 'count'])
            
            for group, stats in group_stats.iterrows():
                group_rate = stats['mean']
                count = stats['count']
                
                # Statistical Significance Check (Heuristic for demo)
                if count < 50: continue # Skip small sample sizes
                
                # Disparate Impact Calculation
                # If a group has < 80% of the positive outcome rate of the mean -> BIAS ALERT
                disparity = group_rate / overall_rate if overall_rate > 0 else 0
                
                metric_key = f"{col}_{group}"
                metrics[metric_key] = round(disparity, 2)

                if disparity < 0.8:
                    issues.append({
                        "feature": col,
                        "group": group,
                        "disparity": f"{disparity:.2f}",
                        "severity": "HIGH" if disparity < 0.6 else "MEDIUM",
                        "details": f"Group receives positive outcome {disparity*100:.1f}% as often as average."
                    })

        return {
            "is_biased": len(issues) > 0,
            "bias_score": 100 - (len(issues) * 15), # Simple score
            "issues": issues,
            "group_metrics": metrics
        }
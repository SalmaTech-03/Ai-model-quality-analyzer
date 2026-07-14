import pandas as pd
from datetime import datetime


class ModelRegistry:
    def __init__(self, db_engine):
        self.db = db_engine

    def get_production_model(self):
        return self.db.get_current_version()

    def register_model(self, version: str, uri: str, metrics: dict):
        record = pd.DataFrame([{
            "version": version,
            "uri": uri,
            "f1": metrics.get("f1"),
            "accuracy": metrics.get("accuracy"),
            "precision": metrics.get("precision"),
            "recall": metrics.get("recall"),
            "created_at": datetime.now(),
        }])
        try:
            record.to_sql("model_artifacts", self.db.conn, if_exists="append", index=False)
            self.db.conn.commit()
        except Exception as e:
            print(f"Registry write failed: {e}")

    def get_model_history(self, limit: int = 10):
        try:
            return pd.read_sql_query(
                "SELECT * FROM model_artifacts ORDER BY created_at DESC LIMIT ?",
                self.db.conn,
                params=(limit,),
            ).to_dict(orient="records")
        except Exception:
            return []

    def execute_rollback(self, reason: str):
        history = self.get_model_history(limit=2)
        curr_v = self.get_production_model()

        if len(history) < 2:
            return {
                "timestamp": datetime.now().isoformat(),
                "action": "ROLLBACK_SKIPPED",
                "reason": "No prior registered version to roll back to.",
                "from_version": curr_v,
            }

        target_v = history[1]["version"]
        self.db.cursor.execute(
            "UPDATE production_state SET value = ?, updated_at = ? WHERE key = 'model_version'",
            (target_v, datetime.now()),
        )
        self.db.conn.commit()

        return {
            "timestamp": datetime.now().isoformat(),
            "action": "ROLLBACK",
            "from_version": curr_v,
            "to_version": target_v,
            "reason": reason,
        }
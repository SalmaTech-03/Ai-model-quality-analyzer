import sqlite3
from datetime import datetime

class ModelRegistry:
    """
    Simulates an MLflow / SageMaker Model Registry.
    Manages pointers to artifacts and handles rollbacks.
    """
    def __init__(self, db_engine):
        self.db = db_engine

    def get_production_model(self):
        # Query existing DB for current version
        return self.db.get_current_version()

    def register_model(self, version, uri, metrics):
        # In a real system, this writes to MLflow
        # Here we simulate logging to DB
        print(f"📦 REGISTRY: Registering {version} (F1: {metrics.get('f1', 0.0)})")
        # Update state
        self.db.upload_dataset("model_artifacts", pd.DataFrame([{
            "version": version, "uri": uri, "f1": metrics.get('f1'), "created_at": datetime.now()
        }]))

    def execute_rollback(self, reason):
        """
        The Mechanics of Rollback:
        1. Find last 'Stable' version in DB.
        2. Update Load Balancer config (Simulated).
        3. Log Incident.
        """
        curr_v = self.get_production_model()
        
        # Simulation: Rollback to v1.0.0
        target_v = "v1.0.0" 
        
        audit_log = {
            "timestamp": datetime.now(),
            "action": "ROLLBACK",
            "from_version": curr_v,
            "to_version": target_v,
            "reason": reason,
            "infrastructure_call": f"kubectl set image deployment/model-serving model={target_v}"
        }
        
        print(f"🔄 ROLLBACK INITIATED: {audit_log}")
        return audit_log
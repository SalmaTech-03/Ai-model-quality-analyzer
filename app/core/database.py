import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

DB_PATH = "modelguard.db"

class DatabaseEngine:
    def __init__(self):
        # check_same_thread=False is required for FastAPI
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_tables()

    def _init_tables(self):
        # 1. Production State (Versioning)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS production_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME
            )
        ''')
        
        # 2. Run History (Audit Logs)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS run_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                risk_score REAL,
                drift_share REAL,
                revenue_at_risk REAL,
                triggered_action TEXT,
                strategy TEXT
            )
        ''')
        
        # --- AUTO-MIGRATION (The Fix for your Error) ---
        # Checks if 'strategy' column exists, if not, adds it.
        try:
            self.cursor.execute("SELECT strategy FROM run_history LIMIT 1")
        except sqlite3.OperationalError:
            print("⚠️ Migrating Database: Adding 'strategy' column...")
            self.cursor.execute("ALTER TABLE run_history ADD COLUMN strategy TEXT")
            self.conn.commit()
        # -----------------------------------------------

        # Seed initial model version if not exists
        self.cursor.execute("INSERT OR IGNORE INTO production_state (key, value, updated_at) VALUES ('model_version', 'v1.0.4', ?)", (datetime.now(),))
        self.conn.commit()

    def check_cooldown(self, hours=24):
        """
        Prevents retraining spam. Returns True if the last critical action 
        happened within the 'hours' window.
        """
        try:
            self.cursor.execute("SELECT timestamp FROM run_history WHERE triggered_action != 'NO ACTION' ORDER BY timestamp DESC LIMIT 1")
            last_run = self.cursor.fetchone()
            
            if not last_run: 
                return False, None
            
            last_time = datetime.fromisoformat(last_run[0])
            if datetime.now() - last_time < timedelta(hours=hours):
                return True, last_time
            return False, None
        except Exception:
            return False, None

    def get_current_version(self):
        try:
            self.cursor.execute("SELECT value FROM production_state WHERE key='model_version'")
            res = self.cursor.fetchone()
            return res[0] if res else "v1.0.0"
        except:
            return "v1.0.0"

    def upload_dataset(self, table_name: str, df: pd.DataFrame):
        """Stores dataframe in SQL for Analyst queries."""
        try:
            df.to_sql(table_name, self.conn, if_exists='replace', index=False)
        except Exception as e:
            print(f"SQL Storage Error: {e}")

    def execute_sql(self, query: str):
        """Runs arbitrary SQL queries."""
        try:
            return pd.read_sql_query(query, self.conn).to_dict(orient='records')
        except Exception as e:
            return {"error": str(e)}

    def log_run(self, drift_share, weighted_score, revenue_risk, action_plan):
        """Audit Log."""
        try:
            self.cursor.execute(
                "INSERT INTO run_history (timestamp, risk_score, drift_share, revenue_at_risk, triggered_action, strategy) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now(), weighted_score, drift_share, revenue_risk, action_plan['action'], action_plan.get('data_strategy', 'N/A'))
            )
            self.conn.commit()
        except Exception as e:
            print(f"❌ DB Log Error: {e}")

    def get_history(self):
        try:
            return pd.read_sql_query("SELECT * FROM run_history ORDER BY timestamp DESC LIMIT 10", self.conn).to_dict(orient='records')
        except:
            return []
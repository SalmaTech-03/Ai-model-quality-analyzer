import os
import sys
import json
import joblib
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, accuracy_score, precision_score, recall_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.core.database import DatabaseEngine
from app.core.registry import ModelRegistry

DATA_PATH = os.path.join(BASE_DIR, "data", "adult_census_reference.csv")
MODEL_DIR = os.path.join(BASE_DIR, "data", "models")
TARGET_COL = "class"

NUMERIC_FEATURES = [
    "age", "fnlwgt", "education-num",
    "capital-gain", "capital-loss", "hours-per-week",
]
CATEGORICAL_FEATURES = [
    "workclass", "education", "marital-status", "occupation",
    "relationship", "race", "sex", "native-country",
]


def load_training_data() -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run `python scripts/download_data.py` first."
        )
    df = pd.read_csv(DATA_PATH)
    df = df.dropna(subset=[TARGET_COL])
    return df


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(transformers=[
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def train_and_evaluate():
    df = load_training_data()
    y = df[TARGET_COL].apply(lambda v: 1 if str(v).strip() == ">50K" else 0)
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    metrics = {
        "f1": round(float(f1_score(y_test, preds)), 4),
        "accuracy": round(float(accuracy_score(y_test, preds)), 4),
        "precision": round(float(precision_score(y_test, preds)), 4),
        "recall": round(float(recall_score(y_test, preds)), 4),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }
    return pipeline, metrics


def next_version(db: DatabaseEngine) -> str:
    try:
        existing = pd.read_sql_query(
            "SELECT version FROM model_artifacts ORDER BY created_at DESC LIMIT 1",
            db.conn,
        )
        if existing.empty:
            return "v1.0.0"
        last = existing.iloc[0]["version"]
        major, minor, patch = last.lstrip("v").split(".")
        return f"v{major}.{minor}.{int(patch) + 1}"
    except Exception:
        return "v1.0.0"


def main():
    pipeline, metrics = train_and_evaluate()
    print(json.dumps(metrics, indent=2))

    os.makedirs(MODEL_DIR, exist_ok=True)
    db = DatabaseEngine()
    registry = ModelRegistry(db)

    version = next_version(db)
    artifact_path = os.path.join(MODEL_DIR, f"adult_census_{version}.joblib")
    joblib.dump(pipeline, artifact_path)

    registry.register_model(version=version, uri=artifact_path, metrics=metrics)

    db.cursor.execute(
        "UPDATE production_state SET value = ?, updated_at = ? WHERE key = 'model_version'",
        (version, datetime.now()),
    )
    db.conn.commit()
    print(f"Registered {version} as active production model.")


if __name__ == "__main__":
    main()
"""
Credit scoring model for India credit risk dataset.

Uses XGBoost (primary) and LightGBM (alternative) for tabular classification.
Wraps model + encoders + metadata into a single CreditScoringModel class
for easy save/load/predict.
"""
import numpy as np
import joblib
import json
from pathlib import Path
from typing import Dict, Optional

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.preprocessing import LabelEncoder


# ====================================================================
#  Model builders
# ====================================================================

def build_xgboost(**kwargs) -> XGBClassifier:
    defaults = dict(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="auc",
        use_label_encoder=False,
        random_state=42,
    )
    defaults.update(kwargs)
    return XGBClassifier(**defaults)


def build_lightgbm(**kwargs) -> LGBMClassifier:
    defaults = dict(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        metric="auc",
        random_state=42,
        verbose=-1,
    )
    defaults.update(kwargs)
    return LGBMClassifier(**defaults)


# ====================================================================
#  CreditScoringModel — wraps everything for serving
# ====================================================================

class CreditScoringModel:
    """
    Bundles the trained model, feature columns, label encoders,
    and metadata for easy save/load/predict.
    """

    def __init__(self):
        self.model = None
        self.feature_columns: list = []
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.metadata: dict = {}

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return P(default) for each row."""
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)

    def predict_single(self, X: np.ndarray) -> Dict:
        """Score one borrower → credit score + risk category + stress stage."""
        prob = float(self.predict_proba(X)[0])

        # Risk category thresholds
        if prob >= 0.30:
            risk = "HIGH"
        elif prob >= 0.10:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        # NPA stress stage (from feature columns if available)
        stage = 0
        stage_label = "Healthy"
        if self.feature_columns:
            try:
                import pandas as pd
                row = pd.DataFrame(X, columns=self.feature_columns)
                if "stress_stage" in row.columns:
                    stage = int(row["stress_stage"].iloc[0])
                from edge_case_features import STRESS_STAGE_LABELS
                stage_label = STRESS_STAGE_LABELS.get(stage, "Unknown")
            except Exception:
                pass

        return {
            "credit_score": round((1 - prob) * 900, 1),
            "default_probability": round(prob, 4),
            "risk_category": risk,
            "stress_stage": stage,
            "stress_stage_label": stage_label,
        }

    # ── Save / Load ───────────────────────────────────────────────

    def save(self, directory: str = "src/model/artifacts"):
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.model, d / "credit_model.joblib")
        joblib.dump(self.feature_columns, d / "feature_columns.joblib")
        joblib.dump(self.label_encoders, d / "label_encoders.joblib")

        if self.metadata:
            with open(d / "model_metadata.json", "w") as f:
                json.dump(self.metadata, f, indent=2)

        print(f"Model saved to {d}")

    @classmethod
    def load(cls, directory: str = "src/model/artifacts") -> "CreditScoringModel":
        d = Path(directory)
        obj = cls()

        obj.model = joblib.load(d / "credit_model.joblib")
        obj.feature_columns = joblib.load(d / "feature_columns.joblib")
        obj.label_encoders = joblib.load(d / "label_encoders.joblib")

        meta_path = d / "model_metadata.json"
        if meta_path.exists():
            with open(meta_path) as f:
                obj.metadata = json.load(f)

        print(f"Model loaded from {d}")
        return obj

"""
Batch scoring pipeline — scores ALL borrowers and saves results.

Data source priority:
  1. PostgreSQL (if connected) — reads from 'borrowers' table
  2. CSV fallback             — reads from Datasets/ folder

Results saved to:
  - PostgreSQL (scoring_results table)  — if connected
  - data/processed/batch_results.csv    — always (file backup)
  - data/processed/batch_summary.json   — always

Can be run:
  1. Manually:      python batch_score.py
  2. Automatically: triggered by app.py scheduler every 48h
  3. Via API:       POST /run-batch
"""
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

from model import CreditScoringModel
from utils import prepare_data, DATASET_PATH

OUTPUT_DIR = Path("data/processed")
RESULTS_PATH = OUTPUT_DIR / "batch_results.csv"
HIGH_RISK_PATH = OUTPUT_DIR / "high_risk.csv"
SUMMARY_PATH = OUTPUT_DIR / "batch_summary.json"


def _load_from_db():
    """Try to load borrowers from PostgreSQL."""
    try:
        from db import get_all_borrowers, test_connection
        if test_connection():
            return get_all_borrowers(), "postgresql"
    except Exception as e:
        print(f"   PostgreSQL not available ({e}), falling back to CSV")
    return None, None


def _load_from_csv():
    """Load borrowers from CSV file."""
    df = pd.read_csv(DATASET_PATH)
    print(f"   Loaded {len(df)} borrowers from CSV")
    return df, "csv"


def run_batch_scoring(data_hash: str = "") -> dict:
    """
    Score every borrower.
    Reads from PostgreSQL if available, otherwise falls back to CSV.
    Returns a summary dict.
    """
    start_time = datetime.now()
    print("=" * 60)
    print(f"  Batch Scoring — {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Load model
    print("\n[1/5] Loading trained model...")
    scoring_model = CreditScoringModel.load("src/model/artifacts")

    # Load data (PostgreSQL first, CSV fallback)
    print("\n[2/5] Loading borrower data...")
    df, source = _load_from_db()
    if df is None:
        df, source = _load_from_csv()
    print(f"   Source: {source} | Rows: {len(df)}")

    borrower_ids = df["borrower_id"].values

    # Drop tracking columns if from PostgreSQL
    for col in ["created_at", "updated_at"]:
        if col in df.columns:
            df = df.drop(columns=[col])

    # Prepare features
    print("\n[3/5] Preprocessing & scoring...")
    X, _, feature_columns, _ = prepare_data(
        df, label_encoders=scoring_model.label_encoders, fit=False,
    )

    # Align features to what the model was trained on (IV-selected subset)
    model_cols = scoring_model.feature_columns
    for col in model_cols:
        if col not in X.columns:
            X[col] = 0
    X_model = X[model_cols]

    # Score all
    probabilities = scoring_model.predict_proba(X_model.values)

    # Build results
    results = pd.DataFrame({
        "borrower_id": borrower_ids,
        "default_probability": np.round(probabilities, 4),
        "credit_score": np.round((1 - probabilities) * 900, 1),
    })

    results["risk_category"] = "LOW"
    results.loc[results["default_probability"] >= 0.10, "risk_category"] = "MEDIUM"
    results.loc[results["default_probability"] >= 0.30, "risk_category"] = "HIGH"

    # Stress stages
    if "stress_stage" in X.columns:
        results["stress_stage"] = X["stress_stage"].values
    else:
        results["stress_stage"] = 0

    from edge_case_features import STRESS_STAGE_LABELS
    results["stress_stage_label"] = results["stress_stage"].map(STRESS_STAGE_LABELS)

    for col in ["stress_score_continuous", "estimated_lgd_inr", "expected_loss_inr",
                 "behavioral_deterioration", "emi_stress"]:
        if col in X.columns:
            results[col] = X[col].values

    # Context columns
    context_cols = [
        "borrower_id", "borrower_segment", "employment_type", "loan_type",
        "state", "borrower_age", "cibil_bureau_score", "monthly_net_income_inr",
        "days_past_due_dpd", "loan_amount_requested_inr",
    ]
    context_cols = [c for c in context_cols if c in df.columns]
    results = results.merge(df[context_cols], on="borrower_id", how="left")

    results = results.sort_values("default_probability", ascending=False)

    # ── Save results ──────────────────────────────────────────────
    print("\n[4/5] Saving results...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Always save to CSV (file backup)
    results.to_csv(RESULTS_PATH, index=False)
    high_risk = results[results["risk_category"] == "HIGH"]
    high_risk.to_csv(HIGH_RISK_PATH, index=False)

    # Save to PostgreSQL if available
    db_saved = False
    try:
        from db import save_scoring_results, save_scoring_run
        save_scoring_results(results)
        db_saved = True
    except Exception as e:
        print(f"   PostgreSQL save skipped ({e})")

    # Summary
    end_time = datetime.now()
    summary = {
        "timestamp": end_time.isoformat(),
        "duration_seconds": round((end_time - start_time).total_seconds(), 2),
        "data_source": source,
        "data_hash": data_hash,
        "total_borrowers": len(results),
        "high_risk_count": int((results["risk_category"] == "HIGH").sum()),
        "medium_risk_count": int((results["risk_category"] == "MEDIUM").sum()),
        "low_risk_count": int((results["risk_category"] == "LOW").sum()),
        "avg_credit_score": round(float(results["credit_score"].mean()), 1),
        "avg_default_probability": round(float(results["default_probability"].mean()), 4),
        "stage_0_healthy": int((results["stress_stage"] == 0).sum()),
        "stage_1_behavioral_risk": int((results["stress_stage"] == 1).sum()),
        "stage_2_early_stress": int((results["stress_stage"] == 2).sum()),
        "stage_3_delinquency": int((results["stress_stage"] == 3).sum()),
        "stage_4_npa": int((results["stress_stage"] == 4).sum()),
        "total_expected_loss_inr": round(float(results.get("expected_loss_inr", pd.Series([0])).sum()), 0),
        "emi_stressed_count": int(results.get("emi_stress", pd.Series([0])).sum()),
        "saved_to_db": db_saved,
    }

    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    # Log the run in PostgreSQL
    if db_saved:
        try:
            save_scoring_run(summary)
        except Exception:
            pass

    # ── Print summary ─────────────────────────────────────────────
    print(f"\n[5/5] Done!")
    print(f"{'=' * 60}")
    print(f"  Source:           {source}")
    print(f"  Total borrowers:  {summary['total_borrowers']:,}")
    print(f"  HIGH risk:        {summary['high_risk_count']:,}")
    print(f"  MEDIUM risk:      {summary['medium_risk_count']:,}")
    print(f"  LOW risk:         {summary['low_risk_count']:,}")
    print(f"  Saved to DB:      {db_saved}")
    print(f"  Time taken:       {summary['duration_seconds']}s")
    print(f"{'=' * 60}\n")

    return summary


if __name__ == "__main__":
    run_batch_scoring()

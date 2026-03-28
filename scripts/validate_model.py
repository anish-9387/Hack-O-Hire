"""
Validate the trained model against Dataset 2 (misaligned columns).

This script:
  1. Loads Dataset 2 (misaligned column names, extra columns, unseen values)
  2. Maps misaligned column names to the expected schema
  3. Drops extra irrelevant columns
  4. Runs the trained model on the cleaned data
  5. Compares predictions against ground truth (actual_default)
  6. Reports accuracy, AUC, precision, recall, confusion matrix

Usage:
    python scripts/validate_model.py
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import (
    roc_auc_score, f1_score, accuracy_score, precision_score, recall_score,
    classification_report, confusion_matrix,
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model import CreditScoringModel
from utils import prepare_data, CATEGORICAL_COLS

ARTIFACTS_DIR = "src/model/artifacts"
DATASET2_PATH = "Datasets/test_dataset_misaligned_5k.csv"

# ── Column mapping: misaligned name → expected name ──────────────────

COLUMN_MAP = {
    "emp_type":              "employment_type",
    "age":                   "borrower_age",
    "dti_ratio":             "debt_to_income_ratio",
    "dpd":                   "days_past_due_dpd",
    "prev_default":          "previous_loan_default_flag",
    "late_payments":         "num_late_payments_12m",
    "credit_util":           "credit_utilisation_ratio",
    "cibil_score":           "cibil_bureau_score",
    "monthly_income":        "monthly_net_income_inr",
    "pti_ratio":             "payment_to_income_ratio_pti",
    "hard_enquiries":        "num_hard_enquiries_12m",
    "txn_frequency":         "txn_frequency_monthly_avg",
    "income_consistency":    "income_consistency_score",
    "revolving_balance":     "revolving_credit_balance_inr",
    "oldest_account_months": "age_oldest_credit_account_months",
    "open_credit_lines":     "num_open_credit_lines",
    "ltv":                   "loan_to_value_ratio_ltv",
    "digital_score":         "digital_engagement_score",
    "utility_score":         "utility_payment_score",
    "loan_amount":           "loan_amount_requested_inr",
}

# Columns that are extra / irrelevant (not in training schema)
EXTRA_COLS = [
    "phone_number", "pan_card", "aadhaar_last_4", "employer_name",
    "marital_status", "num_dependents", "insurance_flag", "bank_account_type",
    "actual_default",  # ground truth — extract before dropping
]

# Value mapping for unseen categorical values
VALUE_MAP = {
    "employment_type": {
        "Freelancer": "Gig/Freelance",  # map unseen → closest known
    },
    "loan_type": {
        "Crypto Loan": "Personal",      # map unseen → safe default
        "Peer-to-Peer": "Personal",
    },
    # Unseen states (Goa, Sikkim) handled by LabelEncoder fallback in prepare_data
}


def load_and_align(path: str) -> tuple[pd.DataFrame, np.ndarray]:
    """Load Dataset 2, align columns, return (aligned_df, ground_truth)."""
    print(f"\n  Loading {path}...")
    df = pd.read_csv(path)
    print(f"  Raw shape: {df.shape[0]} rows × {df.shape[1]} columns")

    # Extract ground truth before dropping
    y_true = df["actual_default"].values.copy()
    print(f"  Ground truth default rate: {y_true.mean()*100:.1f}%")

    # Step 1: Rename misaligned columns
    renamed = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=renamed)
    print(f"  Renamed {len(renamed)} columns")

    # Step 2: Drop extra irrelevant columns
    drop_cols = [c for c in EXTRA_COLS if c in df.columns]
    df = df.drop(columns=drop_cols)
    print(f"  Dropped {len(drop_cols)} extra columns")

    # Step 3: Fix unseen categorical values
    for col, mapping in VALUE_MAP.items():
        if col in df.columns:
            df[col] = df[col].replace(mapping)

    # Step 4: Handle data quality issues
    # Fix zero income → replace with median
    if "monthly_net_income_inr" in df.columns:
        median_income = df.loc[df["monthly_net_income_inr"] > 0, "monthly_net_income_inr"].median()
        df.loc[df["monthly_net_income_inr"] <= 0, "monthly_net_income_inr"] = median_income

    # NaN CIBIL scores → fill with median
    if "cibil_bureau_score" in df.columns:
        df["cibil_bureau_score"] = df["cibil_bureau_score"].fillna(df["cibil_bureau_score"].median())

    # Add synthetic target column for prepare_data (will be extracted but not used)
    df["credit_risk_label"] = 0  # dummy — we use y_true for evaluation
    df["default_probability"] = 0.0  # dummy leaky col
    df["credit_risk_score"] = 0  # dummy leaky col

    print(f"  Aligned shape: {df.shape[0]} rows × {df.shape[1]} columns")
    return df, y_true


def main():
    print("=" * 70)
    print("  Model Validation — Dataset 2 (Misaligned Columns)")
    print("=" * 70)

    # ── Load model ──────────────────────────────────────────
    print("\n[1/4] Loading trained model...")
    model = CreditScoringModel.load(ARTIFACTS_DIR)
    print(f"  Model: {model.metadata.get('model_name', 'Unknown')}")
    print(f"  Features: {len(model.feature_columns)}")
    print(f"  Training AUC: {model.metadata.get('performance', {}).get('test', {}).get('auc', 'N/A')}")

    # ── Load and align Dataset 2 ────────────────────────────
    print("\n[2/4] Loading and aligning Dataset 2...")
    df, y_true = load_and_align(DATASET2_PATH)

    # ── Preprocess using model's encoders ───────────────────
    print("\n[3/4] Preprocessing with trained encoders...")
    X, _, feature_columns, _ = prepare_data(
        df, label_encoders=model.label_encoders, fit=False
    )

    # Align to model's expected feature columns
    for col in model.feature_columns:
        if col not in X.columns:
            X[col] = 0
            print(f"  WARNING: Missing feature '{col}' — filled with 0")
    X = X[model.feature_columns]

    print(f"  Final feature matrix: {X.shape}")

    # ── Run predictions ─────────────────────────────────────
    print("\n[4/4] Running model predictions...")
    probabilities = model.predict_proba(X.values)
    if probabilities.ndim == 2:
        probs = probabilities[:, 1]
    else:
        probs = probabilities

    y_pred = (probs >= 0.5).astype(int)

    # ── Evaluate ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  VALIDATION RESULTS")
    print("=" * 70)

    auc = roc_auc_score(y_true, probs)
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred)
    rec = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)

    print(f"\n  AUC-ROC:    {auc:.4f}")
    print(f"  Accuracy:   {acc:.4f} ({acc*100:.1f}%)")
    print(f"  Precision:  {prec:.4f} ({prec*100:.1f}%)")
    print(f"  Recall:     {rec:.4f} ({rec*100:.1f}%)")
    print(f"  F1 Score:   {f1:.4f}")

    print(f"\n  Confusion Matrix:")
    print(f"    TN={cm[0][0]:>5}  FP={cm[0][1]:>5}  |  Actual Non-Default")
    print(f"    FN={cm[1][0]:>5}  TP={cm[1][1]:>5}  |  Actual Default")

    print(f"\n  Detailed Report:")
    print(classification_report(y_true, y_pred, target_names=["Non-Default", "Default"]))

    # ── Risk Category Breakdown ─────────────────────────────
    risk_cats = pd.cut(probs, bins=[0, 0.10, 0.30, 1.0], labels=["LOW", "MEDIUM", "HIGH"])
    cat_counts = risk_cats.value_counts().sort_index()
    print("  Risk Category Distribution:")
    for cat, count in cat_counts.items():
        pct = count / len(probs) * 100
        actual_default_rate = y_true[risk_cats == cat].mean() * 100 if (risk_cats == cat).sum() > 0 else 0
        print(f"    {cat:8s}: {count:>5} borrowers ({pct:.1f}%)  — actual default rate: {actual_default_rate:.1f}%")

    # ── Verdict ──────────────────────────────────────────────
    print("\n" + "=" * 70)
    if auc >= 0.90:
        print("  PASS: Model handles misaligned data with strong accuracy.")
    elif auc >= 0.80:
        print("  PASS (marginal): Model works but accuracy degraded on misaligned data.")
    else:
        print("  FAIL: Model struggles with misaligned data. Review column mapping.")
    print("=" * 70)


if __name__ == "__main__":
    main()

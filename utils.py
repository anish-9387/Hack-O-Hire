"""
Preprocessing utilities for India credit risk scoring model.
Handles loading, cleaning, encoding, edge case feature engineering,
and preparing the dataset.
"""
import os
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import LabelEncoder, StandardScaler
from typing import Tuple, Dict, Optional, List
import joblib
from dotenv import load_dotenv

load_dotenv()

from edge_case_features import engineer_edge_case_features


# ── Dataset schema ────────────────────────────────────────────────────

DATASET_PATH = os.environ.get("DATASET_PATH", "Datasets/india_credit_risk_dataset_100k.csv")

TARGET_COL = "credit_risk_label"
ID_COL = "borrower_id"

# These are pre-computed targets — must NOT be used as features
LEAK_COLS = ["default_probability", "credit_risk_score"]

# Categorical columns that need encoding
CATEGORICAL_COLS = ["borrower_segment", "employment_type", "loan_type", "state"]

# All numeric feature columns (after dropping ID, target, leaky cols)
NUMERIC_COLS = [
    "is_urban", "borrower_age", "debt_to_income_ratio", "days_past_due_dpd",
    "previous_loan_default_flag", "num_late_payments_12m", "credit_utilisation_ratio",
    "cibil_bureau_score", "monthly_net_income_inr", "payment_to_income_ratio_pti",
    "num_hard_enquiries_12m", "txn_frequency_monthly_avg", "income_consistency_score",
    "revolving_credit_balance_inr", "age_oldest_credit_account_months",
    "num_open_credit_lines", "loan_to_value_ratio_ltv", "digital_engagement_score",
    "utility_payment_score", "loan_amount_requested_inr",
]


# ── Load dataset ──────────────────────────────────────────────────────

def load_dataset(path: str = DATASET_PATH) -> pd.DataFrame:
    """Load the India credit risk dataset."""
    df = pd.read_csv(path)
    print(f"Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")
    return df


# ── Preprocessing pipeline ────────────────────────────────────────────

def prepare_data(
    df: pd.DataFrame,
    label_encoders: Optional[Dict[str, LabelEncoder]] = None,
    fit: bool = True,
) -> Tuple[pd.DataFrame, pd.Series, List[str], Dict[str, LabelEncoder]]:
    """
    Full preprocessing: encode categoricals, handle missing values, return X, y.

    Args:
        df: Raw dataframe
        label_encoders: Pre-fitted encoders (for inference). None = fit new ones.
        fit: If True, fit encoders on this data. If False, use provided encoders.

    Returns:
        X (DataFrame), y (Series), feature_columns (list), label_encoders (dict)
    """
    df = df.copy()

    # ── Engineer edge case features BEFORE dropping anything ─────
    # Needs raw columns like borrower_segment, loan_type, employment_type
    df = engineer_edge_case_features(df)

    # Extract target
    y = df[TARGET_COL].astype(int) if TARGET_COL in df.columns else None

    # Drop ID, target, and leaky columns
    drop_cols = [ID_COL, TARGET_COL] + LEAK_COLS
    drop_cols = [c for c in drop_cols if c in df.columns]
    df = df.drop(columns=drop_cols)

    # ── Encode categorical columns ────────────────────────────────
    if label_encoders is None:
        label_encoders = {}

    for col in CATEGORICAL_COLS:
        if col not in df.columns:
            continue
        if fit:
            le = LabelEncoder()
            # Handle unseen values at inference by adding an "unknown" category
            df[col] = df[col].fillna("unknown")
            le.fit(df[col])
            label_encoders[col] = le
        else:
            le = label_encoders[col]
            df[col] = df[col].fillna("unknown")
            # Map unseen categories to -1
            known = set(le.classes_)
            df[col] = df[col].apply(lambda x: x if x in known else le.classes_[0])

        df[col] = le.transform(df[col])

    # ── Handle missing & infinite values ──────────────────────────
    df = df.select_dtypes(include=[np.number])
    df = df.fillna(df.median())
    df = df.replace([np.inf, -np.inf], 0)

    feature_columns = df.columns.tolist()
    print(f"Prepared {len(feature_columns)} features ({len(CATEGORICAL_COLS)} encoded categoricals + {len(feature_columns) - len(CATEGORICAL_COLS)} numeric)")

    return df, y, feature_columns, label_encoders


# ── Inference helper ──────────────────────────────────────────────────

def features_from_dict(
    data: dict,
    feature_columns: list,
    label_encoders: Dict[str, LabelEncoder],
) -> np.ndarray:
    """
    Convert a single prediction request dict into a feature array.
    Runs edge case feature engineering, then encodes and aligns columns.
    """
    df = pd.DataFrame([data])

    # Run edge case feature engineering on single row
    df = engineer_edge_case_features(df)

    # Encode categoricals
    for col in CATEGORICAL_COLS:
        if col in df.columns and col in label_encoders:
            le = label_encoders[col]
            val = str(df[col].iloc[0])
            known = set(le.classes_)
            df[col] = le.transform([val if val in known else le.classes_[0]])[0]

    # Align columns
    for col in feature_columns:
        if col not in df.columns:
            df[col] = 0
    df = df[feature_columns]
    df = df.fillna(0).replace([np.inf, -np.inf], 0)

    return df.values.astype(np.float32)


# ── Categorical value options (for the UI dropdown) ───────────────────

FIELD_OPTIONS = {
    "borrower_segment": [
        "salaried_urban", "self_employed_msme", "new_to_credit",
        "gig_worker", "rural_agricultural", "salaried_rural",
    ],
    "employment_type": [
        "Salaried", "Self-Employed", "Gig/Freelance", "Agricultural",
    ],
    "loan_type": [
        "Personal", "Home", "Vehicle", "Business", "Education",
        "Gold", "BNPL", "MUDRA", "Consumer Durable",
    ],
    "state": [
        "Maharashtra", "Karnataka", "Tamil Nadu", "Delhi", "Gujarat",
        "West Bengal", "Rajasthan", "Madhya Pradesh", "Uttar Pradesh",
        "Telangana", "Andhra Pradesh", "Kerala", "Bihar", "Punjab",
        "Haryana", "Odisha", "Jharkhand", "Assam", "Chhattisgarh",
    ],
}

# Numeric field metadata for the UI (name, label, min, max, step, default)
NUMERIC_FIELDS = [
    ("is_urban", "Urban Area (0/1)", 0, 1, 1, 1),
    ("borrower_age", "Age", 18, 80, 1, 30),
    ("debt_to_income_ratio", "Debt-to-Income Ratio", 0, 1, 0.01, 0.3),
    ("days_past_due_dpd", "Days Past Due (DPD)", 0, 365, 1, 0),
    ("previous_loan_default_flag", "Previous Default (0/1)", 0, 1, 1, 0),
    ("num_late_payments_12m", "Late Payments (12m)", 0, 20, 1, 0),
    ("credit_utilisation_ratio", "Credit Utilisation Ratio", 0, 1, 0.01, 0.4),
    ("cibil_bureau_score", "CIBIL Score", 300, 900, 1, 700),
    ("monthly_net_income_inr", "Monthly Income (INR)", 5000, 500000, 1000, 50000),
    ("payment_to_income_ratio_pti", "Payment-to-Income Ratio", 0, 1, 0.01, 0.3),
    ("num_hard_enquiries_12m", "Hard Enquiries (12m)", 0, 20, 1, 1),
    ("txn_frequency_monthly_avg", "Avg Monthly Transactions", 0, 200, 1, 50),
    ("income_consistency_score", "Income Consistency Score", 0, 1, 0.01, 0.6),
    ("revolving_credit_balance_inr", "Revolving Credit Balance (INR)", 0, 1000000, 1000, 50000),
    ("age_oldest_credit_account_months", "Oldest Account Age (months)", 0, 600, 1, 60),
    ("num_open_credit_lines", "Open Credit Lines", 0, 20, 1, 3),
    ("loan_to_value_ratio_ltv", "Loan-to-Value Ratio", 0, 1, 0.01, 0.5),
    ("digital_engagement_score", "Digital Engagement Score", 0, 100, 1, 60),
    ("utility_payment_score", "Utility Payment Score", 0, 100, 1, 70),
    ("loan_amount_requested_inr", "Loan Amount Requested (INR)", 10000, 10000000, 10000, 500000),
]

"""
Generate Dataset 2: a test dataset with misaligned columns.

This simulates real-world data that may come from a different system:
  - Some columns renamed (e.g., "age" instead of "borrower_age")
  - Some columns missing (e.g., no "digital_engagement_score")
  - Extra irrelevant columns (e.g., "phone_number", "pan_card")
  - Different categorical values (e.g., "Freelancer" instead of "Gig/Freelance")
  - Different formats (e.g., income as string "50,000" or CIBIL as "NA")
  - Mixed-quality data (NaNs, outliers, edge cases)

The dataset includes known defaulters and non-defaulters so we can
measure the model's accuracy on this misaligned data.

Usage:
    python scripts/generate_test_dataset.py
"""
import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)
N = 5000  # 5K rows

# ── Generate base data with known default patterns ───────────────────

# Create clear defaulter signals for ~20% of rows
is_defaulter = np.random.binomial(1, 0.20, N)

# --- Columns that match Dataset 1 exactly ---
borrower_ids = [f"TEST_{i:05d}" for i in range(N)]

segments = np.random.choice(
    ["salaried_urban", "self_employed_msme", "gig_worker", "rural_agricultural", "new_to_credit"],
    N, p=[0.30, 0.25, 0.20, 0.15, 0.10]
)

# Renamed: "emp_type" instead of "employment_type"
emp_types = np.where(
    is_defaulter,
    np.random.choice(["Gig/Freelance", "Self-Employed", "Agricultural", "Freelancer"], N),
    np.random.choice(["Salaried", "Self-Employed", "Gig/Freelance", "Agricultural"], N),
)

# Some unseen category values
loan_types = np.random.choice(
    ["Personal", "Home", "Vehicle", "Business", "Education", "Gold", "BNPL",
     "Crypto Loan", "Peer-to-Peer", "MUDRA"],  # "Crypto Loan" and "Peer-to-Peer" are unseen
    N
)

states = np.random.choice(
    ["Maharashtra", "Karnataka", "Tamil Nadu", "Delhi", "Gujarat",
     "West Bengal", "Rajasthan", "Goa", "Sikkim"],  # "Goa" and "Sikkim" are unseen
    N
)

is_urban = np.random.choice([0, 1], N, p=[0.3, 0.7])

# Renamed: "age" instead of "borrower_age"
age = np.clip(np.random.normal(35, 12, N).astype(int), 18, 80)

# Defaulters tend to have higher DTI
dti = np.where(is_defaulter, np.clip(np.random.beta(5, 3, N), 0.3, 0.95),
               np.clip(np.random.beta(2, 5, N), 0.05, 0.6))

# Strong signal: DPD
dpd = np.where(is_defaulter, np.random.choice([30, 60, 90, 120, 180], N),
               np.random.choice([0, 0, 0, 0, 5, 10], N))

prev_default = np.where(is_defaulter, np.random.binomial(1, 0.7, N),
                        np.random.binomial(1, 0.05, N))

late_payments = np.where(is_defaulter, np.random.poisson(5, N),
                         np.random.poisson(0.3, N))
late_payments = np.clip(late_payments, 0, 20)

credit_util = np.where(is_defaulter, np.clip(np.random.beta(7, 2, N), 0.5, 1.0),
                       np.clip(np.random.beta(2, 5, N), 0.05, 0.7))

# CIBIL — some as "NA" string, some missing
cibil_raw = np.where(is_defaulter, np.random.normal(450, 80, N),
                     np.random.normal(720, 60, N))
cibil_raw = np.clip(cibil_raw, 300, 900)

# Monthly income — some as formatted strings like "50,000"
income = np.where(is_defaulter, np.random.lognormal(10.2, 0.5, N),
                  np.random.lognormal(10.8, 0.4, N))
income = np.clip(income, 8000, 500000).astype(int)

pti = np.where(is_defaulter, np.clip(np.random.beta(5, 3, N), 0.3, 0.8),
               np.clip(np.random.beta(2, 5, N), 0.05, 0.4))

hard_enquiries = np.where(is_defaulter, np.random.poisson(4, N),
                          np.random.poisson(1, N))
hard_enquiries = np.clip(hard_enquiries, 0, 20)

txn_freq = np.random.poisson(40, N)
txn_freq = np.clip(txn_freq, 5, 200)

income_consistency = np.where(is_defaulter, np.clip(np.random.beta(2, 5, N), 0.1, 0.6),
                              np.clip(np.random.beta(5, 2, N), 0.5, 1.0))

revolving_balance = np.where(is_defaulter, np.random.lognormal(11, 0.8, N),
                             np.random.lognormal(10, 0.6, N))
revolving_balance = np.clip(revolving_balance, 0, 1000000).astype(int)

age_oldest_account = np.where(is_defaulter, np.random.poisson(24, N),
                              np.random.poisson(60, N))
age_oldest_account = np.clip(age_oldest_account, 0, 300)

open_credit_lines = np.random.poisson(3, N)
open_credit_lines = np.clip(open_credit_lines, 1, 15)

ltv = np.where(is_defaulter, np.clip(np.random.beta(6, 3, N), 0.4, 1.0),
               np.clip(np.random.beta(3, 5, N), 0.1, 0.7))

# "digital_score" instead of "digital_engagement_score" (renamed)
digital_score = np.random.randint(0, 100, N)

utility_score = np.where(is_defaulter, np.random.randint(10, 50, N),
                         np.random.randint(50, 100, N))

loan_amount = np.random.lognormal(12, 0.8, N).astype(int)
loan_amount = np.clip(loan_amount, 10000, 10000000)


# ── Build DataFrame with MISALIGNED columns ─────────────────────────

df = pd.DataFrame({
    # Matching columns
    "borrower_id": borrower_ids,
    "borrower_segment": segments,
    "loan_type": loan_types,
    "state": states,
    "is_urban": is_urban,

    # RENAMED columns (model expects different names)
    "emp_type": emp_types,              # should be "employment_type"
    "age": age,                         # should be "borrower_age"
    "dti_ratio": dti.round(4),         # should be "debt_to_income_ratio"
    "dpd": dpd,                        # should be "days_past_due_dpd"
    "prev_default": prev_default,       # should be "previous_loan_default_flag"
    "late_payments": late_payments,      # should be "num_late_payments_12m"
    "credit_util": credit_util.round(4),# should be "credit_utilisation_ratio"
    "cibil_score": cibil_raw.round(1),  # should be "cibil_bureau_score"
    "monthly_income": income,           # should be "monthly_net_income_inr"
    "pti_ratio": pti.round(4),         # should be "payment_to_income_ratio_pti"
    "hard_enquiries": hard_enquiries,   # should be "num_hard_enquiries_12m"
    "txn_frequency": txn_freq,          # should be "txn_frequency_monthly_avg"
    "income_consistency": income_consistency.round(4),  # should be "income_consistency_score"
    "revolving_balance": revolving_balance,  # should be "revolving_credit_balance_inr"
    "oldest_account_months": age_oldest_account,  # should be "age_oldest_credit_account_months"
    "open_credit_lines": open_credit_lines,  # should be "num_open_credit_lines"
    "ltv": ltv.round(4),               # should be "loan_to_value_ratio_ltv"
    "digital_score": digital_score,     # should be "digital_engagement_score"
    "utility_score": utility_score,     # should be "utility_payment_score"
    "loan_amount": loan_amount,         # should be "loan_amount_requested_inr"

    # EXTRA columns (not in training data — should be ignored)
    "phone_number": [f"+91-{np.random.randint(7000000, 9999999)}{np.random.randint(1000,9999)}" for _ in range(N)],
    "pan_card": [f"{''.join(np.random.choice(list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),5))}{''.join(np.random.choice(list('0123456789'),4))}{''.join(np.random.choice(list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),1))}" for _ in range(N)],
    "aadhaar_last_4": np.random.randint(1000, 9999, N),
    "employer_name": np.random.choice(["TCS", "Infosys", "Wipro", "Self", "Reliance", "Flipkart", "NA", ""], N),
    "marital_status": np.random.choice(["Married", "Single", "Divorced", "Widowed"], N),
    "num_dependents": np.random.poisson(2, N),
    "insurance_flag": np.random.binomial(1, 0.4, N),
    "bank_account_type": np.random.choice(["Savings", "Current", "Both"], N),

    # Ground truth (for validation only — model should not see this)
    "actual_default": is_defaulter,
})

# ── Inject some data quality issues ──────────────────────────────────

# Some CIBIL scores as NaN (~3%)
nan_idx = np.random.choice(N, size=int(N * 0.03), replace=False)
df.loc[nan_idx, "cibil_score"] = np.nan

# Some income values as 0 (invalid)
zero_idx = np.random.choice(N, size=int(N * 0.02), replace=False)
df.loc[zero_idx, "monthly_income"] = 0

# ── Save ─────────────────────────────────────────────────────────────

out_path = Path("Datasets/test_dataset_misaligned_5k.csv")
out_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out_path, index=False)

print(f"Dataset 2 generated: {out_path}")
print(f"  Rows: {len(df)}")
print(f"  Columns: {len(df.columns)}")
print(f"  Default rate: {is_defaulter.mean()*100:.1f}%")
print(f"  Misalignments:")
print(f"    - 15 renamed columns (e.g., 'age' vs 'borrower_age')")
print(f"    - 8 extra irrelevant columns (phone, PAN, aadhaar, etc.)")
print(f"    - 2 unseen loan types ('Crypto Loan', 'Peer-to-Peer')")
print(f"    - 2 unseen states ('Goa', 'Sikkim')")
print(f"    - 1 unseen employment type ('Freelancer')")
print(f"    - ~3% CIBIL scores missing (NaN)")
print(f"    - ~2% income values = 0 (invalid)")

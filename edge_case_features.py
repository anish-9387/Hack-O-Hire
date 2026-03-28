"""
Edge Case Feature Engineering

Creates 25+ new features that force the model to handle real-world edge cases
that the raw dataset doesn't capture directly.

Edge cases covered:
  1.  Multi-account health (user has multiple banks, some good, some bad)
  2.  CIBIL missing / new-to-credit handling
  3.  Contradictory signals (good CIBIL + high DPD, etc.)
  4.  Segment bias correction (gig/rural penalized unfairly)
  5.  Reformed borrower detection (past default but currently disciplined)
  6.  Income-adjusted risk (high income shouldn't auto-mean safe)
  7.  Payment discipline composite
  8.  Young borrower risk adjustment
  9.  Loan type risk mismatch
  10. Vulnerability score (combined risk signals)
"""
import numpy as np
import pandas as pd
import json
from pathlib import Path


# Pre-computed segment medians (populated by compute_segment_stats())
_SEGMENT_STATS_PATH = Path("src/model/artifacts/segment_stats.json")
_segment_stats = None


def _get_segment_stats() -> dict:
    """Load pre-computed segment medians (saved during training)."""
    global _segment_stats
    if _segment_stats is None and _SEGMENT_STATS_PATH.exists():
        with open(_SEGMENT_STATS_PATH) as f:
            _segment_stats = json.load(f)
    return _segment_stats or {}


def compute_segment_stats(df: pd.DataFrame) -> dict:
    """Compute and save segment-level medians from the full dataset.
    Called once during training."""
    stats = {}
    for seg in df["borrower_segment"].unique():
        sub = df[df["borrower_segment"] == seg]
        stats[seg] = {
            "income_median": float(sub["monthly_net_income_inr"].median()),
            "dpd_median": float(sub["days_past_due_dpd"].median()),
        }
    _SEGMENT_STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_SEGMENT_STATS_PATH, "w") as f:
        json.dump(stats, f, indent=2)
    global _segment_stats
    _segment_stats = stats
    return stats


def _safe(df: pd.DataFrame, col: str, default=0):
    """Safely get a column, returning default if missing."""
    return df[col] if col in df.columns else default


def engineer_edge_case_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes the raw dataset and adds ~25 new engineered columns.
    Returns the dataframe with new columns appended.
    """
    df = df.copy()

    # Ensure all expected columns exist (for partial prediction dicts)
    _defaults = {
        "num_open_credit_lines": 1, "credit_utilisation_ratio": 0.5,
        "num_late_payments_12m": 0, "cibil_bureau_score": np.nan,
        "loan_to_value_ratio_ltv": np.nan, "age_oldest_credit_account_months": 0,
        "digital_engagement_score": 50, "utility_payment_score": 50,
        "income_consistency_score": 0.5, "days_past_due_dpd": 0,
        "monthly_net_income_inr": 30000, "debt_to_income_ratio": 0.3,
        "payment_to_income_ratio_pti": 0.3, "previous_loan_default_flag": 0,
        "borrower_age": 35, "borrower_segment": "salaried_urban",
        "employment_type": "Salaried", "loan_type": "Personal",
        "loan_amount_requested_inr": 500000, "num_hard_enquiries_12m": 1,
        "txn_frequency_monthly_avg": 50, "revolving_credit_balance_inr": 50000,
        "is_urban": 1, "state": "Maharashtra",
    }
    for col, default_val in _defaults.items():
        if col not in df.columns:
            df[col] = default_val

    # ================================================================
    #  1. MULTI-ACCOUNT HEALTH PROXY
    #     If someone has many credit lines but low utilization and
    #     good payment history, they're likely healthy across accounts.
    #     Penalize only if ALL accounts show stress.
    # ================================================================

    # How well they manage across multiple accounts
    # High score = many accounts, low utilization, no late payments
    df["multi_account_health"] = (
        np.log1p(df["num_open_credit_lines"])
        * (1 - df["credit_utilisation_ratio"].clip(0, 1))
        * (1 - df["num_late_payments_12m"].clip(0, 10) / 10)
    )

    # Diversification benefit: more credit lines + good behavior = safer
    df["account_diversification"] = np.where(
        (df["num_open_credit_lines"] >= 3) & (df["credit_utilisation_ratio"] < 0.5),
        1,  # diversified and healthy
        0,
    )

    # Concentrated risk: few accounts + high utilization
    df["concentrated_risk"] = np.where(
        (df["num_open_credit_lines"] <= 2) & (df["credit_utilisation_ratio"] > 0.7),
        1,
        0,
    )

    # ================================================================
    #  2. CIBIL MISSING / NEW-TO-CREDIT HANDLING
    #     Don't just fill with median — create explicit signals
    # ================================================================

    df["cibil_missing"] = df["cibil_bureau_score"].isnull().astype(int)

    df["ltv_missing"] = df["loan_to_value_ratio_ltv"].isnull().astype(int)

    # For new-to-credit: they have no CIBIL, no history. Model should
    # use alternative data (digital score, utility, income consistency)
    df["is_new_to_credit"] = np.where(
        df["cibil_missing"] == 1,
        1,
        np.where(df["age_oldest_credit_account_months"] == 0, 1, 0),
    )

    # Alternative credit score for thin-file borrowers
    # Uses digital engagement, utility payments, income consistency
    df["alternative_credit_signal"] = (
        df["digital_engagement_score"] / 100 * 0.3
        + df["utility_payment_score"] / 100 * 0.4
        + df["income_consistency_score"] * 0.3
    )

    # ================================================================
    #  3. CONTRADICTORY SIGNAL DETECTORS
    #     When features say opposite things, something unusual is happening
    # ================================================================

    # Good CIBIL but currently struggling (lagging indicator problem)
    cibil_filled = df["cibil_bureau_score"].fillna(650)
    df["good_cibil_high_dpd"] = np.where(
        (cibil_filled > 700) & (df["days_past_due_dpd"] > 90), 1, 0
    )

    # Bad CIBIL but currently clean (recovering borrower)
    df["bad_cibil_clean_now"] = np.where(
        (cibil_filled < 500) & (df["days_past_due_dpd"] == 0) & (df["num_late_payments_12m"] == 0),
        1, 0,
    )

    # High income but high debt burden
    df["high_income_high_dti"] = np.where(
        (df["monthly_net_income_inr"] > 80000) & (df["debt_to_income_ratio"] > 0.6),
        1, 0,
    )

    # Good utility payer but loan defaulter pattern
    df["utility_loan_mismatch"] = np.where(
        (df["utility_payment_score"] > 70) & (df["days_past_due_dpd"] > 60),
        1, 0,
    )

    # Count of contradictory signals (more = more uncertain = needs review)
    df["contradiction_count"] = (
        df["good_cibil_high_dpd"]
        + df["bad_cibil_clean_now"]
        + df["high_income_high_dti"]
        + df["utility_loan_mismatch"]
    )

    # ================================================================
    #  4. SEGMENT BIAS CORRECTION
    #     Gig workers and rural borrowers shouldn't be auto-penalized.
    #     Create features relative to their segment average.
    # ================================================================

    # Income relative to segment (a gig worker earning 50K is different
    # from a salaried person earning 50K)
    # Use pre-computed stats for inference (single rows); groupby for batch
    stats = _get_segment_stats()
    if len(df) < 100 and stats and "borrower_segment" in df.columns:
        # Inference mode: use saved segment medians
        df["income_vs_segment"] = df.apply(
            lambda r: r["monthly_net_income_inr"] / (stats.get(r.get("borrower_segment", ""), {}).get("income_median", 50000) + 1),
            axis=1,
        )
        df["dpd_vs_segment"] = df.apply(
            lambda r: r["days_past_due_dpd"] / (stats.get(r.get("borrower_segment", ""), {}).get("dpd_median", 30) + 1),
            axis=1,
        )
    else:
        # Training mode: compute from the batch
        segment_income_median = df.groupby("borrower_segment")["monthly_net_income_inr"].transform("median")
        df["income_vs_segment"] = df["monthly_net_income_inr"] / (segment_income_median + 1)
        segment_dpd_median = df.groupby("borrower_segment")["days_past_due_dpd"].transform("median")
        df["dpd_vs_segment"] = df["days_past_due_dpd"] / (segment_dpd_median + 1)

    # Is this borrower performing BETTER than their segment average?
    df["outperforms_segment"] = np.where(
        (df["income_vs_segment"] > 1.2)
        & (df["dpd_vs_segment"] < 0.8)
        & (df["income_consistency_score"] > 0.6),
        1, 0,
    )

    # Is this a "responsible gig worker" who shouldn't be penalized?
    df["responsible_gig_worker"] = np.where(
        (df["employment_type"] == "Gig/Freelance")
        & (df["income_consistency_score"] > 0.7)
        & (df["days_past_due_dpd"] < 30)
        & (df["utility_payment_score"] > 60),
        1, 0,
    )

    # Responsible rural borrower
    df["responsible_rural"] = np.where(
        (df["borrower_segment"] == "rural_agricultural")
        & (df["income_consistency_score"] > 0.6)
        & (df["days_past_due_dpd"] < 30)
        & (df["utility_payment_score"] > 50),
        1, 0,
    )

    # ================================================================
    #  5. REFORMED BORROWER DETECTION
    #     Past default + currently disciplined = reformed, not risky
    # ================================================================

    df["reformed_borrower"] = np.where(
        (df["previous_loan_default_flag"] == 1)
        & (df["days_past_due_dpd"] < 15)
        & (df["num_late_payments_12m"] == 0)
        & (df["income_consistency_score"] > 0.6),
        1, 0,
    )

    # How much has borrower improved since last default?
    # Proxy: good current behavior despite past flag
    df["recovery_strength"] = np.where(
        df["previous_loan_default_flag"] == 1,
        (1 - df["days_past_due_dpd"].clip(0, 180) / 180)
        * df["income_consistency_score"]
        * (1 - df["credit_utilisation_ratio"].clip(0, 1)),
        0,  # not applicable if no previous default
    )

    # ================================================================
    #  6. INCOME-ADJUSTED RISK
    #     High income ≠ safe. Adjust for spending patterns.
    # ================================================================

    # Effective disposable income after debt obligations
    df["effective_disposable_income"] = (
        df["monthly_net_income_inr"] * (1 - df["debt_to_income_ratio"])
    )

    # Loan affordability: can they actually afford this loan?
    df["loan_affordability_ratio"] = (
        df["loan_amount_requested_inr"]
        / (df["monthly_net_income_inr"] * 12 + 1)
    )

    # Stress indicator: high PTI + high DTI + low income
    df["financial_stress_index"] = (
        df["payment_to_income_ratio_pti"]
        + df["debt_to_income_ratio"]
        + (1 - df["monthly_net_income_inr"].clip(0, 200000) / 200000)
    ) / 3

    # ================================================================
    #  7. PAYMENT DISCIPLINE COMPOSITE
    #     Single score combining all payment behavior signals
    # ================================================================

    df["payment_discipline_score"] = (
        (1 - df["days_past_due_dpd"].clip(0, 180) / 180) * 0.35
        + (1 - df["num_late_payments_12m"].clip(0, 10) / 10) * 0.25
        + (df["utility_payment_score"] / 100) * 0.20
        + (1 - df["credit_utilisation_ratio"].clip(0, 1)) * 0.20
    )

    # ================================================================
    #  8. YOUNG BORROWER RISK ADJUSTMENT
    #     Young ≠ risky if they show good behavior signals
    # ================================================================

    df["young_but_responsible"] = np.where(
        (df["borrower_age"] <= 28)
        & (df["digital_engagement_score"] > 60)
        & (df["utility_payment_score"] > 60)
        & (df["days_past_due_dpd"] < 30),
        1, 0,
    )

    # Credit history length adjusted for age
    df["credit_history_for_age"] = df["age_oldest_credit_account_months"] / (
        (df["borrower_age"] - 18).clip(1) * 12
    )

    # ================================================================
    #  9. LOAN TYPE RISK INTERACTION
    #     Some loan types are inherently riskier; adjust for borrower quality
    # ================================================================

    high_risk_loans = ["Gold", "BNPL", "Microfinance", "MUDRA", "Microfinance/SHG", "Agricultural/KCC"]
    df["high_risk_loan_type"] = df["loan_type"].isin(high_risk_loans).astype(int)

    # Good borrower + risky loan type = should be treated differently
    # than bad borrower + risky loan type
    df["good_borrower_risky_loan"] = np.where(
        (df["high_risk_loan_type"] == 1)
        & (cibil_filled > 650)
        & (df["income_consistency_score"] > 0.6)
        & (df["days_past_due_dpd"] < 30),
        1, 0,
    )

    # ================================================================
    #  10. OVERALL VULNERABILITY SCORE
    #      How many risk signals are active simultaneously?
    # ================================================================

    df["vulnerability_signals"] = (
        (df["days_past_due_dpd"] > 90).astype(int)
        + (df["previous_loan_default_flag"]).astype(int)
        + (df["num_late_payments_12m"] > 3).astype(int)
        + (df["credit_utilisation_ratio"] > 0.8).astype(int)
        + (df["debt_to_income_ratio"] > 0.6).astype(int)
        + (df["income_consistency_score"] < 0.3).astype(int)
        + (cibil_filled < 500).astype(int)
        + (df["payment_to_income_ratio_pti"] > 0.5).astype(int)
    )

    # Protective signals count
    df["protective_signals"] = (
        (df["income_consistency_score"] > 0.7).astype(int)
        + (cibil_filled > 700).astype(int)
        + (df["days_past_due_dpd"] == 0).astype(int)
        + (df["num_late_payments_12m"] == 0).astype(int)
        + (df["utility_payment_score"] > 70).astype(int)
        + (df["num_open_credit_lines"] >= 3).astype(int)
        + (df["digital_engagement_score"] > 60).astype(int)
    )

    # Net risk: vulnerability minus protection
    df["net_risk_score"] = df["vulnerability_signals"] - df["protective_signals"]

    # ================================================================
    #  11. NPA STRESS STAGES (Chapter 6)
    #      Stage 0: Healthy
    #      Stage 1: Behavioral risk (early signals)
    #      Stage 2: Early stress (deterioration)
    #      Stage 3: Delinquency (missed payments)
    #      Stage 4: NPA (90+ DPD)
    # ================================================================

    dpd = df["days_past_due_dpd"]
    late = df["num_late_payments_12m"]
    consistency = df["income_consistency_score"]
    util = df["credit_utilisation_ratio"]

    # Rule-based stage assignment using multiple signals
    df["stress_stage"] = 0  # default: healthy

    # Stage 1: Behavioral risk — no missed payments yet but warning signs
    stage1_mask = (
        (dpd == 0)
        & (
            (consistency < 0.4)
            | (util > 0.7)
            | (df["debt_to_income_ratio"] > 0.5)
            | (df["num_hard_enquiries_12m"] > 4)
        )
    )
    df.loc[stage1_mask, "stress_stage"] = 1

    # Stage 2: Early stress — small delays, deteriorating behavior
    stage2_mask = (dpd >= 1) & (dpd <= 30) | ((dpd == 0) & (late >= 2) & (consistency < 0.3))
    df.loc[stage2_mask, "stress_stage"] = 2

    # Stage 3: Delinquency — clear missed payments
    stage3_mask = (dpd > 30) & (dpd <= 90)
    df.loc[stage3_mask, "stress_stage"] = 3

    # Stage 4: NPA — 90+ DPD
    stage4_mask = dpd > 90
    df.loc[stage4_mask, "stress_stage"] = 4

    # Continuous stress score (0-100) for granular tracking
    df["stress_score_continuous"] = (
        (dpd.clip(0, 180) / 180) * 30                           # DPD component
        + (late.clip(0, 10) / 10) * 15                          # Late payments
        + (1 - consistency.clip(0, 1)) * 20                     # Income instability
        + util.clip(0, 1) * 15                                  # Credit maxed out
        + df["debt_to_income_ratio"].clip(0, 1) * 10            # Debt burden
        + (1 - df["utility_payment_score"] / 100) * 10          # Utility stress
    ).clip(0, 100)

    # ================================================================
    #  12. EMI STRESS DETECTION (Chapter 3)
    #      High EMI burden = early warning
    # ================================================================

    # EMI burden indicator (PTI > 40% is standard stress threshold)
    df["emi_stress"] = np.where(df["payment_to_income_ratio_pti"] > 0.4, 1, 0)

    # Severe EMI stress (PTI > 55%)
    df["emi_severe_stress"] = np.where(df["payment_to_income_ratio_pti"] > 0.55, 1, 0)

    # EMI affordability gap: how much of income is left after EMI + debt
    df["income_after_obligations"] = (
        df["monthly_net_income_inr"]
        * (1 - df["payment_to_income_ratio_pti"] - df["debt_to_income_ratio"]).clip(0, 1)
    )

    # ================================================================
    #  13. MINIMUM PAYMENT TRAP PROXY (Chapter 8)
    #      No direct data, but high utilization + only small payments
    #      + increasing balance = minimum payment behavior
    # ================================================================

    df["min_payment_trap_risk"] = np.where(
        (df["credit_utilisation_ratio"] > 0.75)
        & (df["revolving_credit_balance_inr"] > 50000)
        & (df["num_late_payments_12m"] <= 1),  # not late, just paying minimum
        1, 0,
    )

    # Credit dependency: using credit for daily needs
    df["credit_dependency"] = np.where(
        (df["credit_utilisation_ratio"] > 0.8)
        & (df["txn_frequency_monthly_avg"] > 80)
        & (df["revolving_credit_balance_inr"] > 100000),
        1, 0,
    )

    # ================================================================
    #  14. OVERLEVERAGED BORROWER (Chapter 2, Persona 3)
    #      Multiple loans + high DTI + high utilization
    # ================================================================

    df["is_overleveraged"] = np.where(
        (df["num_open_credit_lines"] >= 4)
        & (df["debt_to_income_ratio"] > 0.5)
        & (df["credit_utilisation_ratio"] > 0.6),
        1, 0,
    )

    # Leverage severity (continuous)
    df["leverage_severity"] = (
        np.log1p(df["num_open_credit_lines"]) / 3
        * df["debt_to_income_ratio"]
        * df["credit_utilisation_ratio"]
    )

    # ================================================================
    #  15. BNPL / HIGH-RISK PRODUCT SIGNALS (Chapter 3)
    #      BNPL usage = hidden debt, impulse spending
    # ================================================================

    df["is_bnpl"] = (df["loan_type"] == "BNPL").astype(int)
    df["is_microfinance"] = df["loan_type"].isin(["Microfinance", "Microfinance/SHG"]).astype(int)

    # BNPL + low income = very high risk
    df["bnpl_income_risk"] = np.where(
        (df["is_bnpl"] == 1) & (df["monthly_net_income_inr"] < 25000),
        1, 0,
    )

    # ================================================================
    #  16. LGD ESTIMATION (Chapter 9)
    #      Estimated loss if this borrower defaults
    # ================================================================

    # Simple LGD proxy: loan amount * (1 - recovery rate proxy)
    # Recovery rate based on collateral (LTV), income, and loan type
    ltv_filled = df["loan_to_value_ratio_ltv"].fillna(1.0)  # unsecured = 100% LTV
    secured_loans = ["Home", "Vehicle", "Gold", "Equipment"]
    recovery_rate = np.where(
        df["loan_type"].isin(secured_loans),
        (1 - ltv_filled) * 0.6 + 0.3,  # secured: 30-90% recovery
        0.15,  # unsecured: ~15% recovery
    )
    df["estimated_lgd_inr"] = df["loan_amount_requested_inr"] * (1 - np.clip(recovery_rate, 0, 1))

    # Expected loss = PD * LGD (what bank should provision)
    # Use financial_stress_index as PD proxy (0-1)
    df["expected_loss_inr"] = df["financial_stress_index"] * df["estimated_lgd_inr"]

    # ================================================================
    #  17. BEHAVIORAL DETERIORATION SCORE (Chapter 1)
    #      "Defaults are not sudden — they are gradual decline"
    #      Combines multiple early warning signals
    # ================================================================

    df["behavioral_deterioration"] = (
        (df["income_consistency_score"] < 0.4).astype(int) * 2    # Income dropping
        + (df["utility_payment_score"] < 40).astype(int) * 2      # Utility stress
        + (df["credit_utilisation_ratio"] > 0.7).astype(int)      # Credit maxing
        + (df["num_hard_enquiries_12m"] > 3).astype(int)          # Seeking more credit
        + (df["txn_frequency_monthly_avg"] < 20).astype(int)      # Reduced spending
        + (df["digital_engagement_score"] < 30).astype(int)       # Disengagement
        + df["min_payment_trap_risk"]                              # Min payment trap
        + df["emi_stress"]                                         # EMI burden
    )

    # ================================================================
    #  18. CROSS-BANK DEFAULTER SIGNALS (Ecosystem Feature)
    #      If cross-bank data columns are present (injected by
    #      cross_bank.py during batch scoring), create derived features.
    #      During training these default to 0 (no cross-bank data).
    # ================================================================

    # These columns are injected by cross_bank enrichment; default to 0
    for cb_col in [
        "cross_bank_default_flag", "cross_bank_default_count",
        "cross_bank_banks_defaulted", "cross_bank_max_dpd",
        "cross_bank_worst_npa", "cross_bank_serial_defaulter",
        "cross_bank_risk_boost",
    ]:
        if cb_col not in df.columns:
            df[cb_col] = 0

    # Combined cross-bank risk signal (0-1 scale)
    df["cross_bank_risk_signal"] = (
        df["cross_bank_default_flag"] * 0.3
        + np.clip(df["cross_bank_default_count"] / 5, 0, 1) * 0.2
        + np.clip(df["cross_bank_banks_defaulted"] / 3, 0, 1) * 0.2
        + df["cross_bank_serial_defaulter"] * 0.15
        + np.clip(df["cross_bank_max_dpd"] / 365, 0, 1) * 0.15
    )

    # Cross-bank contradiction: appears clean locally but flagged elsewhere
    df["cross_bank_hidden_risk"] = np.where(
        (df["cross_bank_default_flag"] == 1)
        & (df["days_past_due_dpd"] == 0)
        & (df["num_late_payments_12m"] == 0),
        1, 0,
    )

    return df


# List of all new feature column names (for reference)
EDGE_CASE_FEATURES = [
    # Multi-account
    "multi_account_health", "account_diversification", "concentrated_risk",
    # CIBIL / thin file
    "cibil_missing", "ltv_missing", "is_new_to_credit", "alternative_credit_signal",
    # Contradictions
    "good_cibil_high_dpd", "bad_cibil_clean_now", "high_income_high_dti",
    "utility_loan_mismatch", "contradiction_count",
    # Segment bias
    "income_vs_segment", "dpd_vs_segment", "outperforms_segment",
    "responsible_gig_worker", "responsible_rural",
    # Reformed borrower
    "reformed_borrower", "recovery_strength",
    # Income-adjusted
    "effective_disposable_income", "loan_affordability_ratio", "financial_stress_index",
    # Payment discipline
    "payment_discipline_score",
    # Young borrower
    "young_but_responsible", "credit_history_for_age",
    # Loan type
    "high_risk_loan_type", "good_borrower_risky_loan",
    # Vulnerability
    "vulnerability_signals", "protective_signals", "net_risk_score",
    # NPA stages (Ch 6)
    "stress_stage", "stress_score_continuous",
    # EMI stress (Ch 3)
    "emi_stress", "emi_severe_stress", "income_after_obligations",
    # Minimum payment trap (Ch 8)
    "min_payment_trap_risk", "credit_dependency",
    # Overleveraged (Ch 2)
    "is_overleveraged", "leverage_severity",
    # BNPL/product risk (Ch 3)
    "is_bnpl", "is_microfinance", "bnpl_income_risk",
    # LGD (Ch 9)
    "estimated_lgd_inr", "expected_loss_inr",
    # Behavioral deterioration (Ch 1)
    "behavioral_deterioration",
    # Cross-bank ecosystem (Ch 18)
    "cross_bank_default_flag", "cross_bank_default_count",
    "cross_bank_banks_defaulted", "cross_bank_max_dpd",
    "cross_bank_worst_npa", "cross_bank_serial_defaulter",
    "cross_bank_risk_boost", "cross_bank_risk_signal",
    "cross_bank_hidden_risk",
]

# Stage labels for display
STRESS_STAGE_LABELS = {
    0: "Healthy",
    1: "Behavioral Risk",
    2: "Early Stress",
    3: "Delinquency",
    4: "NPA",
}


if __name__ == "__main__":
    df = pd.read_csv("Datasets/india_credit_risk_dataset_100k.csv")
    df = engineer_edge_case_features(df)

    print(f"Total features after engineering: {len(df.columns)}")
    print(f"New edge case features: {len(EDGE_CASE_FEATURES)}")
    print()

    # Validate each edge case
    print("=== EDGE CASE VALIDATION ===\n")

    # 1. Multi-account
    healthy_multi = df[(df["account_diversification"] == 1)]
    print(f"1. Multi-account health:")
    print(f"   Diversified + healthy: {len(healthy_multi)}, default_rate={healthy_multi['credit_risk_label'].mean()*100:.1f}%")
    risky_conc = df[(df["concentrated_risk"] == 1)]
    print(f"   Concentrated risk:     {len(risky_conc)}, default_rate={risky_conc['credit_risk_label'].mean()*100:.1f}%")

    # 4. Segment bias
    resp_gig = df[df["responsible_gig_worker"] == 1]
    all_gig = df[df["employment_type"] == "Gig/Freelance"]
    print(f"\n4. Segment bias correction:")
    print(f"   ALL gig workers:          default_rate={all_gig['credit_risk_label'].mean()*100:.1f}%")
    print(f"   Responsible gig workers:  default_rate={resp_gig['credit_risk_label'].mean()*100:.1f}%  (n={len(resp_gig)})")

    resp_rural = df[df["responsible_rural"] == 1]
    all_rural = df[df["borrower_segment"] == "rural_agricultural"]
    print(f"   ALL rural:                default_rate={all_rural['credit_risk_label'].mean()*100:.1f}%")
    print(f"   Responsible rural:        default_rate={resp_rural['credit_risk_label'].mean()*100:.1f}%  (n={len(resp_rural)})")

    # 5. Reformed
    reformed = df[df["reformed_borrower"] == 1]
    prev_def = df[df["previous_loan_default_flag"] == 1]
    print(f"\n5. Reformed borrower:")
    print(f"   ALL previous defaulters:  default_rate={prev_def['credit_risk_label'].mean()*100:.1f}%")
    print(f"   Reformed borrowers:       default_rate={reformed['credit_risk_label'].mean()*100:.1f}%  (n={len(reformed)})")

    # 3. Contradictions
    contra = df[df["contradiction_count"] > 0]
    print(f"\n3. Contradictory signals:")
    print(f"   Borrowers with 1+ contradictions: {len(contra)}, default_rate={contra['credit_risk_label'].mean()*100:.1f}%")

    # 10. Net risk
    for nr in range(-5, 6):
        sub = df[df["net_risk_score"] == nr]
        if len(sub) > 100:
            print(f"   Net risk={nr:+d}: n={len(sub):>6}, default_rate={sub['credit_risk_label'].mean()*100:.1f}%")

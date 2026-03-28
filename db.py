"""
PostgreSQL database layer.

Handles:
  - Connection management
  - Table creation (borrowers + scoring_results)
  - Loading data from CSV into PostgreSQL
  - Reading borrowers for scoring
  - Saving scoring results
  - Change detection (has data changed since last score?)

Setup:
    1. Install PostgreSQL locally or use a cloud instance
    2. Create a database: CREATE DATABASE credit_risk;
    3. Set DB_URL env var or edit the default below
    4. Run: python load_db.py

Connection string format:
    postgresql://username:password@host:port/database
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# ── Connection ────────────────────────────────────────────────────────

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/credit_risk"
)

_engine = None


def get_engine():
    """Get or create SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(DB_URL, pool_size=5, pool_recycle=3600)
        print(f"Connected to PostgreSQL: {DB_URL.split('@')[-1]}")
    return _engine


def test_connection() -> bool:
    """Test if the database is reachable."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


# ── Table Management ──────────────────────────────────────────────────

def create_tables():
    """Create the borrowers and scoring_results tables if they don't exist."""
    engine = get_engine()
    with engine.connect() as conn:
        # Borrowers table — mirrors the CSV + tracking columns
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS borrowers (
                borrower_id VARCHAR(20) PRIMARY KEY,
                borrower_segment VARCHAR(50),
                employment_type VARCHAR(50),
                loan_type VARCHAR(50),
                state VARCHAR(50),
                is_urban INTEGER,
                borrower_age INTEGER,
                debt_to_income_ratio FLOAT,
                days_past_due_dpd INTEGER,
                previous_loan_default_flag INTEGER,
                num_late_payments_12m INTEGER,
                credit_utilisation_ratio FLOAT,
                cibil_bureau_score FLOAT,
                monthly_net_income_inr FLOAT,
                payment_to_income_ratio_pti FLOAT,
                num_hard_enquiries_12m INTEGER,
                txn_frequency_monthly_avg INTEGER,
                income_consistency_score FLOAT,
                revolving_credit_balance_inr FLOAT,
                age_oldest_credit_account_months INTEGER,
                num_open_credit_lines INTEGER,
                loan_to_value_ratio_ltv FLOAT,
                digital_engagement_score INTEGER,
                utility_payment_score INTEGER,
                loan_amount_requested_inr FLOAT,
                default_probability FLOAT,
                credit_risk_score INTEGER,
                credit_risk_label INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Scoring results table — stores each batch run's output
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS scoring_results (
                id SERIAL PRIMARY KEY,
                borrower_id VARCHAR(20),
                default_probability FLOAT,
                credit_score FLOAT,
                risk_category VARCHAR(10),
                stress_stage INTEGER,
                stress_stage_label VARCHAR(30),
                stress_score_continuous FLOAT,
                estimated_lgd_inr FLOAT,
                expected_loss_inr FLOAT,
                behavioral_deterioration INTEGER,
                emi_stress INTEGER,
                scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Scoring run log — tracks when each batch was run
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS scoring_runs (
                id SERIAL PRIMARY KEY,
                run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_borrowers INTEGER,
                high_risk_count INTEGER,
                medium_risk_count INTEGER,
                low_risk_count INTEGER,
                data_hash VARCHAR(64),
                duration_seconds FLOAT
            )
        """))

        conn.commit()
    print("Tables created/verified")


# ── Load CSV into PostgreSQL ──────────────────────────────────────────

def load_csv_to_db(csv_path: str = "Datasets/india_credit_risk_dataset_100k.csv"):
    """Load the CSV dataset into the borrowers table.
    Replaces existing data."""
    engine = get_engine()
    create_tables()

    print(f"Loading {csv_path} into PostgreSQL...")
    df = pd.read_csv(csv_path)

    # Add tracking columns
    now = datetime.now()
    df["created_at"] = now
    df["updated_at"] = now

    # Write to DB (replace existing)
    df.to_sql("borrowers", engine, if_exists="replace", index=False, method="multi", chunksize=5000)

    print(f"Loaded {len(df)} borrowers into PostgreSQL")
    return len(df)


# ── Read from PostgreSQL ──────────────────────────────────────────────

def get_all_borrowers() -> pd.DataFrame:
    """Read all borrowers from PostgreSQL."""
    engine = get_engine()
    df = pd.read_sql("SELECT * FROM borrowers", engine)
    print(f"Read {len(df)} borrowers from PostgreSQL")
    return df


def get_borrower(borrower_id: str) -> Optional[dict]:
    """Get a single borrower by ID."""
    engine = get_engine()
    df = pd.read_sql(
        "SELECT * FROM borrowers WHERE borrower_id = %(bid)s",
        engine, params={"bid": borrower_id}
    )
    if df.empty:
        return None
    row = df.iloc[0].to_dict()
    # Clean NaN for JSON
    return {k: (None if pd.isna(v) else v) for k, v in row.items()}


def get_borrower_score(borrower_id: str) -> Optional[dict]:
    """Get the latest scoring result for a borrower."""
    engine = get_engine()
    df = pd.read_sql(
        """SELECT * FROM scoring_results
           WHERE borrower_id = %(bid)s
           ORDER BY scored_at DESC LIMIT 1""",
        engine, params={"bid": borrower_id}
    )
    if df.empty:
        return None
    row = df.iloc[0].to_dict()
    return {k: (None if pd.isna(v) else v) for k, v in row.items()}


# ── Save Scoring Results ──────────────────────────────────────────────

def save_scoring_results(results_df: pd.DataFrame):
    """Save batch scoring results to the scoring_results table."""
    engine = get_engine()

    # Select only the columns that match the table
    cols = [
        "borrower_id", "default_probability", "credit_score", "risk_category",
        "stress_stage", "stress_stage_label", "stress_score_continuous",
        "estimated_lgd_inr", "expected_loss_inr", "behavioral_deterioration", "emi_stress",
    ]
    save_df = results_df[[c for c in cols if c in results_df.columns]].copy()
    save_df["scored_at"] = datetime.now()

    save_df.to_sql("scoring_results", engine, if_exists="append", index=False, method="multi", chunksize=5000)
    print(f"Saved {len(save_df)} scoring results to PostgreSQL")


def save_scoring_run(summary: dict):
    """Log a scoring run."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO scoring_runs (total_borrowers, high_risk_count, medium_risk_count, low_risk_count, data_hash, duration_seconds)
            VALUES (:total, :high, :med, :low, :hash, :dur)
        """), {
            "total": summary.get("total_borrowers", 0),
            "high": summary.get("high_risk_count", 0),
            "med": summary.get("medium_risk_count", 0),
            "low": summary.get("low_risk_count", 0),
            "hash": summary.get("data_hash", ""),
            "dur": summary.get("duration_seconds", 0),
        })
        conn.commit()


# ── Change Detection ──────────────────────────────────────────────────

def _compute_data_hash() -> str:
    """Compute a hash of the borrowers table to detect changes.
    Uses row count + max updated_at as a fast fingerprint."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT COUNT(*), MAX(updated_at) FROM borrowers"
        )).fetchone()
        count = result[0] or 0
        max_updated = str(result[1] or "")
        import hashlib
        return hashlib.md5(f"{count}:{max_updated}".encode()).hexdigest()


def _get_last_run_hash() -> Optional[str]:
    """Get the data_hash from the most recent scoring run."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT data_hash FROM scoring_runs ORDER BY run_at DESC LIMIT 1"
            )).fetchone()
            return result[0] if result else None
    except Exception:
        return None


def has_data_changed() -> Tuple[bool, str]:
    """Check if borrowers data has changed since the last scoring run.
    Returns (changed: bool, current_hash: str)."""
    current_hash = _compute_data_hash()
    last_hash = _get_last_run_hash()

    if last_hash is None:
        return True, current_hash  # Never scored before

    changed = current_hash != last_hash
    return changed, current_hash


# ── High-Risk Query ───────────────────────────────────────────────────

def get_high_risk_borrowers(limit: int = 100) -> list:
    """Get the top high-risk borrowers from the latest scoring run."""
    engine = get_engine()
    try:
        df = pd.read_sql(f"""
            SELECT sr.*, b.borrower_segment, b.state, b.cibil_bureau_score,
                   b.days_past_due_dpd, b.monthly_net_income_inr, b.loan_type
            FROM scoring_results sr
            JOIN borrowers b ON sr.borrower_id = b.borrower_id
            WHERE sr.scored_at = (SELECT MAX(scored_at) FROM scoring_results)
              AND sr.risk_category = 'HIGH'
            ORDER BY sr.default_probability DESC
            LIMIT {limit}
        """, engine)
        return df.to_dict(orient="records")
    except Exception:
        return []


if __name__ == "__main__":
    print("Testing database connection...")
    if test_connection():
        print("Connection OK")
        create_tables()
        print("Tables ready")
    else:
        print("FAILED — check your PostgreSQL is running and DB_URL is correct")
        print(f"Current DB_URL: {DB_URL}")

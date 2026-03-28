"""
User Portal — borrower-facing app.
A borrower logs in with their ID and sees their personal credit risk status.

Data source priority:
  1. PostgreSQL (if connected) — real-time data
  2. CSV fallback             — static dataset

Runs on port 8001 (separate from the company dashboard on port 8000).

Usage:
    uvicorn user_app:app --reload --port 8001
"""
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path
from typing import Optional
import pandas as pd

app = FastAPI(title="Credit Risk - User Portal", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

STATIC_DIR = Path("static")
RESULTS_DIR = Path("data/processed")
DATASET_PATH = os.environ.get("DATASET_PATH", "Datasets/india_credit_risk_dataset_100k.csv")

# Whether PostgreSQL is available
_db_available = False
# Fallback: in-memory CSV data (only used if DB is down)
_csv_borrowers: Optional[pd.DataFrame] = None
_csv_scores: Optional[pd.DataFrame] = None


@app.on_event("startup")
async def startup():
    global _db_available, _csv_borrowers, _csv_scores

    # Try PostgreSQL first
    try:
        from db import test_connection
        if test_connection():
            _db_available = True
            print("User portal: connected to PostgreSQL")
            return
    except Exception:
        pass

    # Fallback to CSV
    print("User portal: PostgreSQL not available, using CSV fallback")
    try:
        _csv_borrowers = pd.read_csv(DATASET_PATH)
        print(f"  Loaded {len(_csv_borrowers)} borrowers from CSV")
    except Exception as e:
        print(f"  Could not load CSV: {e}")

    results_path = RESULTS_DIR / "batch_results.csv"
    if results_path.exists():
        try:
            _csv_scores = pd.read_csv(results_path)
            print(f"  Loaded {len(_csv_scores)} scored results from CSV")
        except Exception:
            pass


def _get_user_from_db(borrower_id: str) -> Optional[dict]:
    """Fetch borrower + latest score from PostgreSQL."""
    from db import get_borrower, get_borrower_score
    user = get_borrower(borrower_id)
    if user is None:
        return None
    score = get_borrower_score(borrower_id)
    if score:
        user["credit_score"] = score.get("credit_score", 0)
        user["default_probability"] = score.get("default_probability", 0)
        user["risk_category"] = score.get("risk_category", "UNKNOWN")
        user["stress_stage"] = score.get("stress_stage", 0)
        user["stress_stage_label"] = score.get("stress_stage_label", "Unknown")
    return user


def _get_user_from_csv(borrower_id: str) -> Optional[dict]:
    """Fetch borrower from in-memory CSV data."""
    if _csv_borrowers is None:
        return None
    row = _csv_borrowers[_csv_borrowers["borrower_id"] == borrower_id]
    if row.empty:
        return None
    user = row.iloc[0].to_dict()

    # Get score from batch results
    if _csv_scores is not None:
        score_row = _csv_scores[_csv_scores["borrower_id"] == borrower_id]
        if not score_row.empty:
            sr = score_row.iloc[0]
            user["credit_score"] = float(sr.get("credit_score", 0))
            user["default_probability"] = float(sr.get("default_probability", 0))
            user["risk_category"] = sr.get("risk_category", "UNKNOWN")

    # Fallback if no batch scores
    if "credit_score" not in user:
        dp = user.get("default_probability", 0)
        dp = float(dp) if pd.notna(dp) else 0
        user["credit_score"] = round((1 - dp) * 900, 1)
        user["default_probability"] = dp
        user["risk_category"] = "HIGH" if dp >= 0.30 else "MEDIUM" if dp >= 0.10 else "LOW"

    # Clean NaN
    return {k: (None if pd.isna(v) else (round(v, 4) if isinstance(v, float) else v)) for k, v in user.items()}


@app.get("/", response_class=HTMLResponse)
async def login_page():
    return HTMLResponse(content=(STATIC_DIR / "user_login.html").read_text())


@app.get("/dashboard/{borrower_id}", response_class=HTMLResponse)
async def user_dashboard(borrower_id: str):
    html = (STATIC_DIR / "user_dashboard.html").read_text()
    return HTMLResponse(content=html.replace("__BORROWER_ID__", borrower_id))


@app.get("/api/user/{borrower_id}")
async def get_user_data(borrower_id: str):
    """Return all data for a single borrower. Reads from DB or CSV."""
    user = None

    if _db_available:
        try:
            user = _get_user_from_db(borrower_id)
        except Exception:
            user = _get_user_from_csv(borrower_id)
    else:
        user = _get_user_from_csv(borrower_id)

    if user is None:
        raise HTTPException(404, f"Borrower {borrower_id} not found")

    return user


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("user_app:app", host="0.0.0.0", port=8001, reload=True)

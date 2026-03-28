"""
Company Dashboard — admin-facing analytics app.
Shows portfolio risk analytics, charts, batch results, and high-risk borrowers.

Runs on port 8000.
User portal runs separately on port 8001 (user_app.py).

Usage:
    uvicorn app:app --reload --port 8000
"""
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from pathlib import Path
import json
import threading

import numpy as np
import pandas as pd

from model import CreditScoringModel
from utils import features_from_dict, FIELD_OPTIONS, NUMERIC_FIELDS, CATEGORICAL_COLS

# ── Configuration (from .env) ────────────────────────────────────────

BATCH_INTERVAL_HOURS = int(os.environ.get("BATCH_INTERVAL_HOURS", "48"))
ARTIFACTS_DIR = os.environ.get("MODEL_ARTIFACTS_DIR", "src/model/artifacts")
RESULTS_DIR = Path("data/processed")
STATIC_DIR = Path("static")
DATASET_PATH = "Datasets/india_credit_risk_dataset_100k.csv"

# ── App setup ─────────────────────────────────────────────────────────

app = FastAPI(
    title="Credit Risk - Company Dashboard",
    description="Portfolio risk analytics and batch scoring",
    version="2.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Global state ──────────────────────────────────────────────────────

scoring_model: Optional[CreditScoringModel] = None
scheduler = None
last_batch_summary: Optional[dict] = None


def _load_last_summary():
    global last_batch_summary
    p = RESULTS_DIR / "batch_summary.json"
    if p.exists():
        try:
            with open(p) as f:
                last_batch_summary = json.load(f)
        except (json.JSONDecodeError, ValueError):
            last_batch_summary = None


def _run_batch_job():
    """Scheduler job: check if DB has changed, rescore only if needed."""
    global last_batch_summary
    try:
        # Check if PostgreSQL data has changed
        data_hash = ""
        try:
            from db import has_data_changed
            changed, data_hash = has_data_changed()
            if not changed:
                print(f"[Scheduler] No data changes detected. Skipping rescore.")
                return
            print(f"[Scheduler] Data change detected (hash: {data_hash[:8]}...)")
        except Exception:
            print(f"[Scheduler] DB check unavailable, proceeding with rescore")

        from batch_score import run_batch_scoring
        print(f"[Scheduler] Batch re-scoring at {datetime.now().isoformat()}")
        last_batch_summary = run_batch_scoring(data_hash=data_hash)
        print(f"[Scheduler] Done. HIGH risk: {last_batch_summary['high_risk_count']}")
    except Exception as e:
        print(f"[Scheduler] Batch failed: {e}")


@app.on_event("startup")
async def startup():
    global scoring_model, scheduler
    try:
        scoring_model = CreditScoringModel.load(ARTIFACTS_DIR)
        print("Model loaded")
    except Exception as e:
        print(f"Model not loaded: {e}. Run: python train.py")

    _load_last_summary()

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(_run_batch_job, "interval", hours=BATCH_INTERVAL_HOURS, id="batch_scoring", next_run_time=None)
        scheduler.start()
        print(f"Scheduler: every {BATCH_INTERVAL_HOURS}h")
    except ImportError:
        print("APScheduler not installed. pip install apscheduler")


@app.on_event("shutdown")
async def shutdown():
    if scheduler:
        scheduler.shutdown()


# ── Schemas ───────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    borrower_segment: str = "salaried_urban"
    employment_type: str = "Salaried"
    loan_type: str = "Personal"
    state: str = "Maharashtra"
    is_urban: int = 1
    borrower_age: int = 30
    debt_to_income_ratio: float = 0.3
    days_past_due_dpd: int = 0
    previous_loan_default_flag: int = 0
    num_late_payments_12m: int = 0
    credit_utilisation_ratio: float = 0.4
    cibil_bureau_score: float = 700
    monthly_net_income_inr: float = 50000
    payment_to_income_ratio_pti: float = 0.3
    num_hard_enquiries_12m: int = 1
    txn_frequency_monthly_avg: int = 50
    income_consistency_score: float = 0.6
    revolving_credit_balance_inr: float = 50000
    age_oldest_credit_account_months: int = 60
    num_open_credit_lines: int = 3
    loan_to_value_ratio_ltv: float = 0.5
    digital_engagement_score: int = 60
    utility_payment_score: int = 70
    loan_amount_requested_inr: float = 500000


class PredictResponse(BaseModel):
    credit_score: float
    default_probability: float
    risk_category: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ── API Endpoints ─────────────────────────────────────────────────────

@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    if scoring_model is None:
        raise HTTPException(503, "Model not loaded")
    X = features_from_dict(req.dict(), scoring_model.feature_columns, scoring_model.label_encoders)
    return scoring_model.predict_single(X)


@app.post("/run-batch")
async def trigger_batch():
    if scoring_model is None:
        raise HTTPException(503, "Model not loaded")
    threading.Thread(target=_run_batch_job, daemon=True).start()
    return {"status": "started", "timestamp": datetime.now().isoformat()}


@app.get("/health")
async def health():
    next_run = None
    if scheduler:
        job = scheduler.get_job("batch_scoring")
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()
    return {
        "status": "healthy" if scoring_model else "model_not_loaded",
        "scheduler": "running" if scheduler and scheduler.running else "disabled",
        "batch_interval_hours": BATCH_INTERVAL_HOURS,
        "next_batch_run": next_run,
        "last_batch": last_batch_summary.get("timestamp") if last_batch_summary else None,
    }


@app.get("/model-info")
async def model_info():
    if scoring_model is None:
        raise HTTPException(503, "Model not loaded")
    return scoring_model.metadata


@app.get("/batch-summary")
async def batch_summary():
    _load_last_summary()
    if last_batch_summary is None:
        raise HTTPException(404, "No batch results yet")
    return last_batch_summary


@app.get("/high-risk-data")
async def high_risk_data():
    p = RESULTS_DIR / "high_risk.csv"
    if not p.exists():
        return []
    try:
        hr = pd.read_csv(p).head(100)
        return json.loads(hr.to_json(orient="records"))
    except Exception:
        return []


@app.get("/analytics-data")
async def analytics_data():
    """Compute all analytics from the batch results for the charts."""
    results_path = RESULTS_DIR / "batch_results.csv"
    if not results_path.exists():
        raise HTTPException(404, "No batch results. Run batch scoring first.")

    df = pd.read_csv(results_path)

    # Also load original dataset for richer breakdowns
    try:
        orig = pd.read_csv(DATASET_PATH)
        df = df.merge(
            orig[["borrower_id", "borrower_age", "employment_type", "loan_type", "monthly_net_income_inr"]],
            on="borrower_id", how="left", suffixes=("", "_orig"),
        )
    except Exception:
        pass

    # Risk distribution
    risk_counts = df["risk_category"].value_counts().to_dict()

    # Risk by state (top 10 states by high risk count)
    risk_by_state = {}
    if "state" in df.columns:
        state_risk = df.groupby("state")["risk_category"].value_counts().unstack(fill_value=0)
        for cat in ["HIGH", "MEDIUM", "LOW"]:
            if cat not in state_risk.columns:
                state_risk[cat] = 0
        top_states = state_risk.sort_values("HIGH", ascending=False).head(10)
        risk_by_state = {
            "labels": top_states.index.tolist(),
            "high": top_states["HIGH"].tolist(),
            "medium": top_states["MEDIUM"].tolist(),
            "low": top_states["LOW"].tolist(),
        }

    # Risk by segment
    risk_by_segment = {}
    if "borrower_segment" in df.columns:
        seg = df.groupby("borrower_segment")["risk_category"].value_counts().unstack(fill_value=0)
        for cat in ["HIGH", "MEDIUM", "LOW"]:
            if cat not in seg.columns:
                seg[cat] = 0
        risk_by_segment = {
            "labels": [s.replace("_", " ").title() for s in seg.index.tolist()],
            "high": seg["HIGH"].tolist(),
            "medium": seg["MEDIUM"].tolist(),
            "low": seg["LOW"].tolist(),
        }

    # Risk by loan type
    risk_by_loan = {}
    lt_col = "loan_type" if "loan_type" in df.columns else "loan_type_orig"
    if lt_col in df.columns:
        lt = df.groupby(lt_col)["risk_category"].value_counts().unstack(fill_value=0)
        for cat in ["HIGH", "MEDIUM", "LOW"]:
            if cat not in lt.columns:
                lt[cat] = 0
        risk_by_loan = {
            "labels": lt.index.tolist(),
            "high": lt["HIGH"].tolist(),
            "medium": lt["MEDIUM"].tolist(),
            "low": lt["LOW"].tolist(),
        }

    # Credit score distribution (histogram)
    bins = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]
    hist, _ = np.histogram(df["credit_score"].dropna(), bins=bins)
    score_dist = {
        "labels": [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins)-1)],
        "counts": hist.tolist(),
    }

    # Default probability distribution
    prob_bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    prob_hist, _ = np.histogram(df["default_probability"].dropna(), bins=prob_bins)
    prob_dist = {
        "labels": [f"{int(prob_bins[i]*100)}-{int(prob_bins[i+1]*100)}%" for i in range(len(prob_bins)-1)],
        "counts": prob_hist.tolist(),
    }

    # Age group risk (if available)
    age_risk = {}
    age_col = "borrower_age" if "borrower_age" in df.columns else "borrower_age_orig"
    if age_col in df.columns:
        df["age_group"] = pd.cut(df[age_col], bins=[18, 25, 35, 45, 55, 80], labels=["18-25", "26-35", "36-45", "46-55", "56+"])
        ag = df.groupby("age_group", observed=True)["risk_category"].value_counts().unstack(fill_value=0)
        for cat in ["HIGH", "MEDIUM", "LOW"]:
            if cat not in ag.columns:
                ag[cat] = 0
        age_risk = {
            "labels": ag.index.tolist(),
            "high": ag["HIGH"].tolist(),
            "medium": ag["MEDIUM"].tolist(),
            "low": ag["LOW"].tolist(),
        }

    # Top risk factors (feature importance from model)
    feature_imp = {}
    if scoring_model and hasattr(scoring_model.model, "feature_importances_"):
        imp = scoring_model.model.feature_importances_
        cols = scoring_model.feature_columns
        top_idx = np.argsort(imp)[::-1][:10]
        feature_imp = {
            "labels": [cols[i].replace("_", " ").title() for i in top_idx],
            "values": [round(float(imp[i]), 4) for i in top_idx],
        }

    return {
        "risk_counts": risk_counts,
        "risk_by_state": risk_by_state,
        "risk_by_segment": risk_by_segment,
        "risk_by_loan": risk_by_loan,
        "score_distribution": score_dist,
        "probability_distribution": prob_dist,
        "age_risk": age_risk,
        "feature_importance": feature_imp,
    }


@app.get("/")
async def root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    html = (STATIC_DIR / "dashboard.html").read_text()
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

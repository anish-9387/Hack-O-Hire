"""
Cross-Bank Defaulter Detection Ecosystem

Simulates a shared inter-bank defaulter registry (like CIBIL/RBI CRILC).
When a customer defaults at Bank A, that record is shared. If the same
customer applies at Bank B (appearing as "new" and "clean"), the system
detects the cross-bank default history and boosts the risk score.

Key concepts:
  - PAN + phone hash is the composite matching key (privacy-preserving)
  - Banks report defaults → central registry
  - On new application, registry is queried
  - Cross-bank features are injected into the ML pipeline

Tables:
  - participating_banks: banks in the ecosystem
  - cross_bank_defaults: shared default records
"""
import hashlib
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


# ── Composite Key Hashing (Privacy-Preserving) ───────────────────────

_HASH_SALT = os.environ.get("CROSSBANK_HASH_SALT", "hack-o-hire-2026")


def hash_identity(pan: str, phone: str) -> str:
    """Create a privacy-preserving composite hash from PAN + phone.
    This is the matching key across banks — no raw PII is stored."""
    raw = f"{pan.strip().upper()}:{phone.strip()}"
    return hashlib.sha256(f"{_HASH_SALT}:{raw}".encode()).hexdigest()


# ── In-Memory Registry (file-backed, no PostgreSQL dependency) ────────

_REGISTRY_PATH = Path("data/cross_bank_registry.json")
_BANKS_PATH = Path("data/participating_banks.json")
_registry_cache = None
_banks_cache = None


def _ensure_dirs():
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_registry() -> list:
    global _registry_cache
    if _registry_cache is not None:
        return _registry_cache
    if _REGISTRY_PATH.exists():
        with open(_REGISTRY_PATH) as f:
            _registry_cache = json.load(f)
    else:
        _registry_cache = []
    return _registry_cache


def _save_registry(data: list):
    global _registry_cache
    _ensure_dirs()
    _registry_cache = data
    with open(_REGISTRY_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _load_banks() -> list:
    global _banks_cache
    if _banks_cache is not None:
        return _banks_cache
    if _BANKS_PATH.exists():
        with open(_BANKS_PATH) as f:
            _banks_cache = json.load(f)
    else:
        _banks_cache = []
    return _banks_cache


def _save_banks(data: list):
    global _banks_cache
    _ensure_dirs()
    _banks_cache = data
    with open(_BANKS_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ── DB Table Creation (PostgreSQL, optional) ──────────────────────────

def create_cross_bank_tables():
    """Create cross-bank tables in PostgreSQL (if connected)."""
    try:
        from db import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS participating_banks (
                    bank_id VARCHAR(20) PRIMARY KEY,
                    bank_name VARCHAR(100) NOT NULL,
                    bank_code VARCHAR(20) UNIQUE NOT NULL,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    total_defaults_reported INTEGER DEFAULT 0
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cross_bank_defaults (
                    id SERIAL PRIMARY KEY,
                    identity_hash VARCHAR(64) NOT NULL,
                    reporting_bank_id VARCHAR(20) NOT NULL,
                    borrower_name_masked VARCHAR(50),
                    default_amount_inr FLOAT,
                    default_date DATE,
                    loan_type VARCHAR(50),
                    days_past_due INTEGER,
                    account_status VARCHAR(30) DEFAULT 'defaulted',
                    npa_stage INTEGER DEFAULT 4,
                    resolution_status VARCHAR(30) DEFAULT 'unresolved',
                    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(identity_hash, reporting_bank_id, default_date)
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_crossbank_hash
                ON cross_bank_defaults(identity_hash)
            """))
            conn.commit()
        print("Cross-bank tables created in PostgreSQL")
    except Exception as e:
        print(f"PostgreSQL cross-bank tables skipped ({e}), using file-based registry")


# ── Bank Management ───────────────────────────────────────────────────

def register_bank(bank_id: str, bank_name: str, bank_code: str) -> dict:
    """Register a bank in the ecosystem."""
    banks = _load_banks()
    for b in banks:
        if b["bank_id"] == bank_id or b["bank_code"] == bank_code:
            return {"status": "exists", "bank": b}
    bank = {
        "bank_id": bank_id,
        "bank_name": bank_name,
        "bank_code": bank_code,
        "joined_at": datetime.now().isoformat(),
        "is_active": True,
        "total_defaults_reported": 0,
    }
    banks.append(bank)
    _save_banks(banks)
    return {"status": "registered", "bank": bank}


def get_participating_banks() -> list:
    """Get all participating banks."""
    return _load_banks()


# ── Default Reporting ─────────────────────────────────────────────────

def report_default(
    pan: str,
    phone: str,
    reporting_bank_id: str,
    borrower_name: str = "",
    default_amount_inr: float = 0,
    default_date: str = "",
    loan_type: str = "Personal",
    days_past_due: int = 90,
    npa_stage: int = 4,
) -> dict:
    """
    Report a borrower default to the shared registry.
    Called by a bank when a borrower defaults on a loan.
    """
    identity_hash = hash_identity(pan, phone)

    # Mask borrower name for privacy (show first 2 + last 2 chars)
    if borrower_name:
        name_masked = borrower_name[:2] + "***" + borrower_name[-2:] if len(borrower_name) > 4 else "***"
    else:
        name_masked = "***"

    record = {
        "identity_hash": identity_hash,
        "reporting_bank_id": reporting_bank_id,
        "borrower_name_masked": name_masked,
        "default_amount_inr": default_amount_inr,
        "default_date": default_date or datetime.now().strftime("%Y-%m-%d"),
        "loan_type": loan_type,
        "days_past_due": days_past_due,
        "account_status": "defaulted" if days_past_due >= 90 else "delinquent",
        "npa_stage": npa_stage,
        "resolution_status": "unresolved",
        "reported_at": datetime.now().isoformat(),
    }

    registry = _load_registry()

    # Check for duplicate (same hash + bank + date)
    for existing in registry:
        if (existing["identity_hash"] == identity_hash
                and existing["reporting_bank_id"] == reporting_bank_id
                and existing["default_date"] == record["default_date"]):
            return {"status": "duplicate", "message": "Default already reported"}

    registry.append(record)
    _save_registry(registry)

    # Update bank's reported count
    banks = _load_banks()
    for b in banks:
        if b["bank_id"] == reporting_bank_id:
            b["total_defaults_reported"] = b.get("total_defaults_reported", 0) + 1
    _save_banks(banks)

    return {
        "status": "reported",
        "identity_hash": identity_hash,
        "record_count": len([r for r in registry if r["identity_hash"] == identity_hash]),
    }


# ── Cross-Bank Query ──────────────────────────────────────────────────

def check_cross_bank_defaults(
    pan: str,
    phone: str,
    exclude_bank_id: str = "",
) -> dict:
    """
    Check if a borrower has defaults at OTHER banks.
    Called when a new loan application is received.

    Args:
        pan: Borrower's PAN number
        phone: Borrower's phone number
        exclude_bank_id: The querying bank's ID (exclude own records)

    Returns:
        Cross-bank default summary with risk signals
    """
    identity_hash = hash_identity(pan, phone)
    registry = _load_registry()

    # Find all defaults for this identity at OTHER banks
    matches = [
        r for r in registry
        if r["identity_hash"] == identity_hash
        and r["reporting_bank_id"] != exclude_bank_id
    ]

    if not matches:
        return {
            "found": False,
            "cross_bank_default_count": 0,
            "total_default_amount": 0,
            "banks_defaulted_at": 0,
            "max_dpd_other_banks": 0,
            "worst_npa_stage": 0,
            "is_serial_defaulter": False,
            "risk_boost": 0.0,
            "records": [],
        }

    # Aggregate cross-bank signals
    unique_banks = set(r["reporting_bank_id"] for r in matches)
    total_amount = sum(r.get("default_amount_inr", 0) for r in matches)
    max_dpd = max(r.get("days_past_due", 0) for r in matches)
    worst_npa = max(r.get("npa_stage", 0) for r in matches)
    unresolved = sum(1 for r in matches if r.get("resolution_status") == "unresolved")
    is_serial = len(unique_banks) >= 2  # Defaulted at 2+ other banks

    # Calculate risk boost (0.0 to 0.5 added to default_probability)
    risk_boost = _calculate_risk_boost(
        default_count=len(matches),
        banks_count=len(unique_banks),
        total_amount=total_amount,
        max_dpd=max_dpd,
        unresolved_count=unresolved,
    )

    return {
        "found": True,
        "cross_bank_default_count": len(matches),
        "total_default_amount": total_amount,
        "banks_defaulted_at": len(unique_banks),
        "max_dpd_other_banks": max_dpd,
        "worst_npa_stage": worst_npa,
        "is_serial_defaulter": is_serial,
        "unresolved_count": unresolved,
        "risk_boost": risk_boost,
        "records": [
            {
                "bank": r["reporting_bank_id"],
                "amount": r.get("default_amount_inr", 0),
                "date": r.get("default_date", ""),
                "loan_type": r.get("loan_type", ""),
                "dpd": r.get("days_past_due", 0),
                "npa_stage": r.get("npa_stage", 0),
                "status": r.get("resolution_status", ""),
            }
            for r in matches
        ],
    }


def _calculate_risk_boost(
    default_count: int,
    banks_count: int,
    total_amount: float,
    max_dpd: int,
    unresolved_count: int,
) -> float:
    """
    Calculate how much to boost the default probability based on
    cross-bank default history.

    Returns a value between 0.0 and 0.50 (added to the model's prediction).
    """
    boost = 0.0

    # Base boost for having any cross-bank default
    boost += 0.10

    # More defaults = higher risk (capped contribution)
    boost += min(default_count * 0.03, 0.09)

    # Multiple banks = serial defaulter pattern
    if banks_count >= 2:
        boost += 0.08
    if banks_count >= 3:
        boost += 0.05

    # High DPD at other banks
    if max_dpd >= 180:
        boost += 0.05
    elif max_dpd >= 90:
        boost += 0.03

    # Large default amounts (> 5L)
    if total_amount > 500000:
        boost += 0.05
    elif total_amount > 100000:
        boost += 0.02

    # Unresolved defaults are worse than resolved ones
    boost += min(unresolved_count * 0.03, 0.06)

    return min(boost, 0.50)  # Cap at 0.50


# ── Feature Engineering for ML Pipeline ───────────────────────────────

def get_cross_bank_features(pan: str, phone: str, exclude_bank_id: str = "") -> dict:
    """
    Generate ML features from cross-bank default data.
    These features are injected into the model's feature vector.
    """
    result = check_cross_bank_defaults(pan, phone, exclude_bank_id)

    return {
        "cross_bank_default_flag": 1 if result["found"] else 0,
        "cross_bank_default_count": result["cross_bank_default_count"],
        "cross_bank_total_default_amount": result["total_default_amount"],
        "cross_bank_banks_defaulted": result["banks_defaulted_at"],
        "cross_bank_max_dpd": result["max_dpd_other_banks"],
        "cross_bank_worst_npa": result["worst_npa_stage"],
        "cross_bank_serial_defaulter": 1 if result["is_serial_defaulter"] else 0,
        "cross_bank_risk_boost": result["risk_boost"],
    }


def enrich_prediction_with_cross_bank(
    prediction: dict,
    pan: str = "",
    phone: str = "",
    exclude_bank_id: str = "",
) -> dict:
    """
    Enrich a model prediction with cross-bank default intelligence.
    Called after the model predicts, to boost risk if cross-bank defaults exist.

    Args:
        prediction: Model output dict (credit_score, default_probability, risk_category)
        pan: Borrower PAN
        phone: Borrower phone

    Returns:
        Enhanced prediction with cross-bank signals
    """
    if not pan or not phone:
        prediction["cross_bank_check"] = {"status": "skipped", "reason": "no PAN/phone provided"}
        return prediction

    cb_result = check_cross_bank_defaults(pan, phone, exclude_bank_id)

    if not cb_result["found"]:
        prediction["cross_bank_check"] = {
            "status": "clear",
            "message": "No cross-bank defaults found",
        }
        return prediction

    # Boost the default probability
    original_prob = prediction.get("default_probability", 0)
    boosted_prob = min(original_prob + cb_result["risk_boost"], 0.99)

    # Recalculate risk category
    if boosted_prob >= 0.30:
        new_category = "HIGH"
    elif boosted_prob >= 0.10:
        new_category = "MEDIUM"
    else:
        new_category = "LOW"

    # Adjust credit score (inversely proportional to risk boost)
    original_score = prediction.get("credit_score", 700)
    score_penalty = cb_result["risk_boost"] * 300  # up to 150 points
    adjusted_score = max(100, original_score - score_penalty)

    prediction["original_default_probability"] = original_prob
    prediction["default_probability"] = round(boosted_prob, 4)
    prediction["original_risk_category"] = prediction.get("risk_category", "")
    prediction["risk_category"] = new_category
    prediction["original_credit_score"] = original_score
    prediction["credit_score"] = round(adjusted_score, 1)

    prediction["cross_bank_check"] = {
        "status": "flagged",
        "message": f"Defaulter at {cb_result['banks_defaulted_at']} other bank(s)",
        "defaults_found": cb_result["cross_bank_default_count"],
        "banks_defaulted_at": cb_result["banks_defaulted_at"],
        "total_default_amount": cb_result["total_default_amount"],
        "max_dpd_other_banks": cb_result["max_dpd_other_banks"],
        "is_serial_defaulter": cb_result["is_serial_defaulter"],
        "risk_boost_applied": cb_result["risk_boost"],
        "records": cb_result["records"],
    }

    return prediction


# ── Seed Demo Data ────────────────────────────────────────────────────

def seed_demo_data():
    """
    Populate the registry with realistic demo data for demonstration.
    Simulates 5 banks and ~50 defaulters with cross-bank patterns.
    """
    # Register demo banks
    demo_banks = [
        ("BANK_SBI", "State Bank of India", "SBI"),
        ("BANK_HDFC", "HDFC Bank", "HDFC"),
        ("BANK_ICICI", "ICICI Bank", "ICICI"),
        ("BANK_AXIS", "Axis Bank", "AXIS"),
        ("BANK_PNB", "Punjab National Bank", "PNB"),
    ]
    for bid, name, code in demo_banks:
        register_bank(bid, name, code)

    rng = random.Random(42)

    # Generate 50 defaulters with cross-bank patterns
    demo_defaults = []
    pan_prefixes = ["ABCPD", "XYZPL", "MNRPK", "PQRST", "JKLMN"]
    loan_types = ["Personal", "Home", "Vehicle", "Business", "Education", "Gold", "BNPL"]

    for i in range(50):
        pan = f"{rng.choice(pan_prefixes)}{1000 + i}A"
        phone = f"98{rng.randint(10000000, 99999999)}"
        name = f"Demo Borrower {i+1}"

        # Some borrowers default at multiple banks (serial defaulters)
        if i < 10:
            # Serial defaulters: 2-3 banks
            num_banks = rng.randint(2, 3)
        elif i < 25:
            # Single cross-bank default
            num_banks = 1
        else:
            # Single bank default (won't trigger cross-bank for their own bank)
            num_banks = 1

        banks_for_default = rng.sample(demo_banks, min(num_banks, len(demo_banks)))

        for bank_id, _, _ in banks_for_default:
            dpd = rng.randint(30, 365)
            amount = rng.randint(50000, 2000000)
            days_ago = rng.randint(30, 730)
            default_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

            report_default(
                pan=pan,
                phone=phone,
                reporting_bank_id=bank_id,
                borrower_name=name,
                default_amount_inr=amount,
                default_date=default_date,
                loan_type=rng.choice(loan_types),
                days_past_due=dpd,
                npa_stage=4 if dpd >= 90 else (3 if dpd >= 30 else 2),
            )

    registry = _load_registry()
    banks = _load_banks()
    print(f"Seeded cross-bank registry: {len(banks)} banks, {len(registry)} default records")
    return {"banks": len(banks), "records": len(registry)}


# ── Registry Statistics ───────────────────────────────────────────────

def get_registry_stats() -> dict:
    """Get summary statistics of the cross-bank registry."""
    registry = _load_registry()
    banks = _load_banks()

    if not registry:
        return {
            "total_records": 0,
            "unique_defaulters": 0,
            "participating_banks": len(banks),
            "serial_defaulters": 0,
            "total_default_amount": 0,
            "unresolved_count": 0,
        }

    unique_hashes = set(r["identity_hash"] for r in registry)

    # Serial defaulters: appeared at 2+ banks
    hash_bank_count = {}
    for r in registry:
        h = r["identity_hash"]
        if h not in hash_bank_count:
            hash_bank_count[h] = set()
        hash_bank_count[h].add(r["reporting_bank_id"])
    serial = sum(1 for banks_set in hash_bank_count.values() if len(banks_set) >= 2)

    total_amount = sum(r.get("default_amount_inr", 0) for r in registry)
    unresolved = sum(1 for r in registry if r.get("resolution_status") == "unresolved")

    # Per-bank breakdown
    bank_breakdown = {}
    for r in registry:
        bid = r["reporting_bank_id"]
        if bid not in bank_breakdown:
            bank_breakdown[bid] = {"count": 0, "amount": 0}
        bank_breakdown[bid]["count"] += 1
        bank_breakdown[bid]["amount"] += r.get("default_amount_inr", 0)

    return {
        "total_records": len(registry),
        "unique_defaulters": len(unique_hashes),
        "participating_banks": len(banks),
        "active_banks": sum(1 for b in banks if b.get("is_active")),
        "serial_defaulters": serial,
        "total_default_amount": total_amount,
        "unresolved_count": unresolved,
        "bank_breakdown": bank_breakdown,
        "banks": [
            {
                "id": b["bank_id"],
                "name": b["bank_name"],
                "code": b["bank_code"],
                "defaults_reported": bank_breakdown.get(b["bank_id"], {}).get("count", 0),
            }
            for b in banks
        ],
    }


if __name__ == "__main__":
    print("=== Cross-Bank Defaulter Detection System ===\n")

    # Seed demo data
    result = seed_demo_data()
    print(f"\nRegistry stats:")
    stats = get_registry_stats()
    for k, v in stats.items():
        if k not in ("bank_breakdown", "banks"):
            print(f"  {k}: {v}")

    # Demo: check a known defaulter
    print("\n--- Demo: Checking a known serial defaulter ---")
    # Use same PAN/phone as first demo defaulter
    rng = random.Random(42)
    pan = f"{rng.choice(['ABCPD', 'XYZPL', 'MNRPK', 'PQRST', 'JKLMN'])}{1000}A"
    phone = f"98{rng.randint(10000000, 99999999)}"
    print(f"PAN: {pan}, Phone: {phone}")

    result = check_cross_bank_defaults(pan, phone, exclude_bank_id="BANK_NEW")
    print(f"Found: {result['found']}")
    print(f"Defaults at other banks: {result['cross_bank_default_count']}")
    print(f"Banks defaulted at: {result['banks_defaulted_at']}")
    print(f"Serial defaulter: {result['is_serial_defaulter']}")
    print(f"Risk boost: +{result['risk_boost']:.2f}")

    # Demo: check a clean person
    print("\n--- Demo: Checking a clean person ---")
    result = check_cross_bank_defaults("CLEANPAN1234A", "9800000000", exclude_bank_id="BANK_NEW")
    print(f"Found: {result['found']}")
    print(f"Risk boost: +{result['risk_boost']:.2f}")

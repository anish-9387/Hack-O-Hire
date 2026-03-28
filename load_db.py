"""
Load the CSV dataset into PostgreSQL and set up all tables.

Run this ONCE after setting up PostgreSQL:
    python load_db.py

Prerequisites:
    1. PostgreSQL running
    2. Database created: createdb risk_sense  (or whatever DATABASE_URL points to)
    3. Set DATABASE_URL in .env

What this does:
    1. Creates all tables (borrowers, scoring_results, scoring_runs, audit_logs, interventions)
    2. Loads india_credit_risk_dataset_100k.csv into the borrowers table
    3. Verifies the data is loaded correctly
"""
import os
from dotenv import load_dotenv
load_dotenv()

from db import load_csv_to_db, get_engine, create_tables, test_connection
from sqlalchemy import text

DATASET_PATH = os.environ.get("DATASET_PATH", "Datasets/india_credit_risk_dataset_100k.csv")


def main():
    print("=" * 60)
    print("  RiskSense — Database Setup")
    print("=" * 60)

    # Step 1: Test connection
    print("\n[1/4] Testing database connection...")
    if not test_connection():
        print("\nFAILED. Make sure PostgreSQL is running.")
        print("Quick setup:")
        print("  # Windows (after installing PostgreSQL):")
        print("  psql -U postgres -c \"CREATE DATABASE risk_sense;\"")
        print("\nOr set DATABASE_URL in .env:")
        print("  DATABASE_URL=postgresql://postgres:yourpass@localhost:5432/risk_sense")
        return

    # Step 2: Create tables
    print("\n[2/4] Creating tables...")
    create_tables()

    # Step 3: Load CSV
    print(f"\n[3/4] Loading {DATASET_PATH} into PostgreSQL...")
    count = load_csv_to_db(DATASET_PATH)

    # Step 4: Verify
    print("\n[4/4] Verifying...")
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM borrowers")).fetchone()
        print(f"  Rows in borrowers table: {result[0]}")

        result = conn.execute(text(
            "SELECT borrower_segment, COUNT(*) FROM borrowers GROUP BY borrower_segment ORDER BY COUNT(*) DESC"
        ))
        print("  By segment:")
        for row in result:
            print(f"    {row[0]:30s} {row[1]:>6}")

        # Check all tables exist
        for table in ["borrowers", "scoring_results", "scoring_runs", "audit_logs", "interventions"]:
            r = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
            print(f"  {table}: {r[0]} rows")

    print(f"\nDone! {count} borrowers loaded into PostgreSQL.")
    print("Run the app:  uvicorn app:app --reload --port 8000")


if __name__ == "__main__":
    main()

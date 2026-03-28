"""
Load the CSV dataset into PostgreSQL.

Run this ONCE after setting up PostgreSQL:
    python load_db.py

Prerequisites:
    1. PostgreSQL running (brew services start postgresql OR docker)
    2. Database created: createdb credit_risk
    3. (Optional) Set DATABASE_URL env var, or edit db.py default

What this does:
    1. Creates tables (borrowers, scoring_results, scoring_runs)
    2. Loads india_credit_risk_dataset_100k.csv into the borrowers table
    3. Verifies the data is loaded correctly
"""
from db import load_csv_to_db, get_engine, create_tables, test_connection
from sqlalchemy import text


def main():
    print("=" * 60)
    print("  Loading Dataset into PostgreSQL")
    print("=" * 60)

    # Step 1: Test connection
    print("\n[1/3] Testing database connection...")
    if not test_connection():
        print("\nFAILED. Make sure PostgreSQL is running.")
        print("Quick setup:")
        print("  brew install postgresql@15     # macOS")
        print("  brew services start postgresql@15")
        print("  createdb credit_risk")
        print("\nOr set DATABASE_URL:")
        print("  export DATABASE_URL=postgresql://user:pass@localhost:5432/credit_risk")
        return

    # Step 2: Load CSV
    print("\n[2/3] Loading CSV into PostgreSQL...")
    count = load_csv_to_db("Datasets/india_credit_risk_dataset_100k.csv")

    # Step 3: Verify
    print("\n[3/3] Verifying...")
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

    print(f"\nDone! {count} borrowers loaded into PostgreSQL.")
    print("You can now run: uvicorn app:app --reload --port 8000")


if __name__ == "__main__":
    main()

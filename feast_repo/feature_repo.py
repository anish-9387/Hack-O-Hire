"""
Feast Feature Store Configuration for Financial Stress Prediction
Defines feature views and entities for real-time feature serving
"""
from datetime import timedelta
from feast import Entity, FeatureView, Field, FileSource, ValueType
from feast.types import Float32, Float64, Int64, String

# Define Customer Entity
customer = Entity(
    name="customer_id",
    description="Unique identifier for bank customers",
    value_type=ValueType.INT64
)

# Define data source (file-based for local development)
financial_features_source = FileSource(
    path="../data/processed/engineered_features.parquet",
    timestamp_field="timestamp",
)

# Define Feature View for Financial Behavior
financial_behavior_fv = FeatureView(
    name="financial_behavior_features",
    description="Behavioral features for financial stress prediction",
    entities=[customer],
    ttl=timedelta(days=30),
    schema=[
        # Salary Features
        Field(name="days_since_last_salary", dtype=Float32),
        Field(name="avg_salary_amount", dtype=Float32),
        Field(name="salary_delay_trend", dtype=Float32),
        Field(name="salary_variance", dtype=Float32),
        Field(name="months_with_salary", dtype=Int64),
        
        # Balance Features
        Field(name="current_balance", dtype=Float32),
        Field(name="min_balance_30d", dtype=Float32),
        Field(name="balance_drop_pct_4weeks", dtype=Float32),
        Field(name="balance_trend", dtype=Float32),
        Field(name="avg_daily_balance", dtype=Float32),
        
        # UPI Features
        Field(name="upi_to_loan_apps_pct", dtype=Float32),
        Field(name="upi_to_loan_apps_count", dtype=Int64),
        Field(name="total_upi_count", dtype=Int64),
        Field(name="avg_upi_amount", dtype=Float32),
        Field(name="upi_loan_amount_30d", dtype=Float32),
        
        # Spending Category Ratios
        Field(name="essential_spend_ratio", dtype=Float32),
        Field(name="discretionary_spend_ratio", dtype=Float32),
        Field(name="cash_withdrawal_ratio", dtype=Float32),
        
        # Payment Behavior
        Field(name="avg_bill_payment_day", dtype=Float32),
        Field(name="bill_payment_delay_trend", dtype=Float32),
        Field(name="failed_autopay_count", dtype=Int64),
        
        # ATM Features
        Field(name="atm_withdrawal_count_30d", dtype=Int64),
        Field(name="atm_withdrawal_amount_30d", dtype=Float32),
        Field(name="avg_atm_amount", dtype=Float32),
        
        # Transaction Velocity
        Field(name="txn_count_30d", dtype=Int64),
        Field(name="txn_count_7d", dtype=Int64),
        Field(name="avg_txn_per_day", dtype=Float32),
        Field(name="debit_count_30d", dtype=Int64),
        Field(name="credit_count_30d", dtype=Int64),
    ],
    online=True,
    source=financial_features_source,
    tags={"team": "risk_analytics", "use_case": "stress_prediction"}
)

# Define Feature View for Customer Profile
customer_profile_source = FileSource(
    path="../data/processed/customer_profiles_synthetic.parquet",
    timestamp_field="timestamp",
)

customer_profile_fv = FeatureView(
    name="customer_profile_features",
    description="Static customer profile features",
    entities=[customer],
    ttl=timedelta(days=365),
    schema=[
        Field(name="age", dtype=Int64),
        Field(name="monthly_income", dtype=Float32),
        Field(name="location", dtype=String),
        Field(name="account_age_months", dtype=Int64),
        Field(name="credit_score", dtype=Int64),
    ],
    online=True,
    source=customer_profile_source,
    tags={"team": "risk_analytics"}
)

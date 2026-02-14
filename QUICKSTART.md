# 🚀 Quick Start Guide - Financial Stress Prediction System

This guide will help you get the system up and running in 15 minutes.

## Prerequisites
- Python 3.10+
- 4GB RAM minimum
- (Optional) Docker for Kafka

## Step-by-Step Setup

### 1. Install Dependencies (5 min)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Generate Data (5 min)

```bash
# Generate synthetic transaction data
python src/utils/synthetic_data_generator.py

# This creates 1000 customers with 6 months of transaction history
# Output: data/raw/synthetic_transactions.csv
```

### 3. Engineer Features (2 min)

```bash
# Calculate behavioral features from transactions
python src/features/feature_engineering.py

# Output: data/processed/engineered_features.csv
```

### 4. Train Model (3 min)

Option A - Jupyter Notebook (Recommended):
```bash
# Start Jupyter
jupyter notebook

# Open and run: notebooks/model_training.ipynb
# Run all cells (Kernel → Restart & Run All)
```

Option B - Python Script (if notebook doesn't work):
```bash
# Note: Training script needs to be created if notebook fails
# The notebook will save the model to src/model/artifacts/
```

### 5. Start API Server (1 min)

```bash
python app/main.py
```

API will be available at:
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 6. Start Dashboard (1 min)

Open a new terminal:

```bash
python src/dashboard/dashboard_app.py
```

Dashboard will be available at:
- **URL**: http://localhost:8050

## Quick Test

### Test the API:

```bash
# Windows PowerShell:
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/score/example" -Method Get

# Mac/Linux:
curl http://localhost:8000/api/v1/score/example
```

Expected output:
```json
{
  "risk_score": 0.7234,
  "prediction": "Stressed",
  "risk_level": "MEDIUM",
  ...
}
```

### Test the Dashboard:

1. Open http://localhost:8050
2. You should see:
   - Summary cards with customer counts
   - Risk distribution charts
   - Top at-risk customers table
3. Try filtering by "High Risk" in the dropdown

## Troubleshooting

### Issue: "Model not found"
**Solution**: Make sure you ran the model training notebook and saved the model.

### Issue: "No data files found"
**Solution**: Run the data generation scripts:
```bash
python src/utils/synthetic_data_generator.py
python src/features/feature_engineering.py
```

### Issue: "Port already in use"
**Solution**: Change ports in `app/config.yaml`:
```yaml
api:
  port: 8001  # Change from 8000
dashboard:
  port: 8051  # Change from 8050
```

### Issue: API returns 500 errors
**Solution**: Check if model is trained and artifacts exist:
```bash
# Should see these files:
ls src/model/artifacts/
# - financial_stress_model.joblib
# - feature_columns.joblib
# - model_metadata.json
```

## Optional: Kafka Real-time Processing

If you want to test real-time transaction processing:

### 1. Start Kafka (Docker required)

```bash
docker-compose up kafka zookeeper -d
```

### 2. Start Producer (simulates transactions)

```bash
python src/ingestion/kafka_producer.py
```

### 3. Start Consumer (processes transactions)

Open another terminal:
```bash
python src/ingestion/kafka_consumer.py
```

Press Ctrl+C to stop at any time.

## What's Next?

1. **Explore the Dashboard**: Filter by risk levels, analyze customers
2. **Test API Endpoints**: Try `/api/v1/score` with custom data
3. **Review SHAP Explanations**: Check why customers are high-risk
4. **Monitor Alerts**: Check `logs/alerts.log` for high-risk alerts
5. **Customize**: Edit `app/config.yaml` to change thresholds

## Common Use Cases

### Score a Custom Customer:

```python
import requests

data = {
    "customer_id": 99999,
    "days_since_last_salary": 60,
    "balance_drop_pct_4weeks": 45,
    "upi_to_loan_apps_pct": 35,
    "failed_autopay_count": 5
}

response = requests.post(
    "http://localhost:8000/api/v1/score",
    json=data
)

print(response.json())
```

### Get Model Performance:

```python
import requests

response = requests.get("http://localhost:8000/api/v1/model/info")
print(response.json())
```

## Need Help?

- Check the full [README.md](README.md)
- Review API docs at http://localhost:8000/docs
- Check logs in `logs/` directory

## Success Checklist

- [ ] Dependencies installed
- [ ] Data generated
- [ ] Features engineered
- [ ] Model trained
- [ ] API running (port 8000)
- [ ] Dashboard running (port 8050)
- [ ] API test successful
- [ ] Dashboard loads correctly

If all items are checked, you're good to go! 🎉

---

**Estimated Total Time**: 15-20 minutes

**Next Steps**: Explore the notebooks for detailed analysis and model insights!

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/raw data/processed logs src/model/artifacts

# Expose ports
# 8000 for FastAPI
# 8050 for Dash dashboard
EXPOSE 8000 8050

# Default command (can be overridden)
CMD ["python", "app/main.py"]

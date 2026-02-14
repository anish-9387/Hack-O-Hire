"""
Setup script to initialize the Financial Stress Prediction System
Runs all necessary steps to prepare the system
"""
import sys
from pathlib import Path
import subprocess

def print_step(step_num, total_steps, description):
    """Print step header"""
    print("\n" + "="*70)
    print(f"STEP {step_num}/{total_steps}: {description}")
    print("="*70)

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n▶ {description}...")
    try:
        subprocess.run(command, check=True, shell=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False

def main():
    """Main setup workflow"""
    print("\n" + "="*70)
    print("🚀 FINANCIAL STRESS PREDICTION SYSTEM - SETUP")
    print("="*70)
    print("\nThis script will:")
    print("  1. Create necessary directories")
    print("  2. Generate synthetic transaction data")
    print("  3. Engineer features from transactions")
    print("  4. Prepare data for model training")
    print("\nEstimated time: 5-10 minutes")
    print("\nPress Ctrl+C to cancel at any time")
    print("="*70)
    
    input("\nPress ENTER to continue...")
    
    total_steps = 4
    
    # Step 1: Create directories
    print_step(1, total_steps, "Creating Directory Structure")
    directories = [
        'data/raw',
        'data/processed',
        'logs',
        'logs/alerts',
        'src/model/artifacts',
        'ppt_assets'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created: {directory}")
    
    print("✅ All directories created")
    
    # Step 2: Generate synthetic data
    print_step(2, total_steps, "Generating Synthetic Transaction Data")
    print("This will create 1000 customers with 6 months of transaction history...")
    
    if not run_command(
        f"{sys.executable} src/utils/synthetic_data_generator.py",
        "Synthetic data generation"
    ):
        print("\n⚠️ Failed to generate synthetic data")
        print("You can try running manually:")
        print(f"  {sys.executable} src/utils/synthetic_data_generator.py")
        return
    
    # Step 3: Merge datasets (if Kaggle data exists)
    print_step(3, total_steps, "Merging Datasets")
    print("Checking for Kaggle datasets...")
    
    run_command(
        f"{sys.executable} src/utils/data_merger.py",
        "Dataset merging"
    )
    # Don't fail if this doesn't work - it's optional
    
    # Step 4: Engineer features
    print_step(4, total_steps, "Engineering Features")
    print("Calculating 30+ behavioral features from transactions...")
    
    if not run_command(
        f"{sys.executable} src/features/feature_engineering.py",
        "Feature engineering"
    ):
        print("\n⚠️ Failed to engineer features")
        print("You can try running manually:")
        print(f"  {sys.executable} src/features/feature_engineering.py")
        return
    
    # Success!
    print("\n" + "="*70)
    print("✅ SETUP COMPLETED SUCCESSFULLY!")
    print("="*70)
    
    print("\n📋 What was created:")
    print("  ✓ Synthetic transaction data (data/raw/)")
    print("  ✓ Engineered features (data/processed/)")
    print("  ✓ Directory structure")
    
    print("\n📝 Next Steps:")
    print("\n1. Train the ML model:")
    print("   Option A (Recommended): Open and run notebooks/model_training.ipynb")
    print("   Option B: Run training script (if available)")
    
    print("\n2. Start the API server:")
    print(f"   {sys.executable} app/main.py")
    print("   Then visit: http://localhost:8000/docs")
    
    print("\n3. Start the dashboard:")
    print(f"   {sys.executable} src/dashboard/dashboard_app.py")
    print("   Then visit: http://localhost:8050")
    
    print("\n4. (Optional) Test real-time processing:")
    print("   - Start Kafka: docker-compose up kafka zookeeper -d")
    print(f"   - Start producer: {sys.executable} src/ingestion/kafka_producer.py")
    print(f"   - Start consumer: {sys.executable} src/ingestion/kafka_consumer.py")
    
    print("\n📚 For detailed instructions, see:")
    print("   - README.md (full documentation)")
    print("   - QUICKSTART.md (15-minute quick start)")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)

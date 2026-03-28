"""
Training pipeline for India credit risk scoring.

Full research-backed pipeline:
  1. Load dataset
  2. Preprocess + edge case feature engineering (69 features)
  3. Information Value (IV) feature selection
  4. SMOTEENN imbalance handling
  5. Train LightGBM (primary) + XGBoost (benchmark)
  6. Probability calibration (Platt scaling)
  7. SHAP explainability
  8. PCA variance analysis
  9. Evaluate + save everything

Usage:
    python train.py                    # full pipeline (LightGBM + XGBoost)
    python train.py --model xgboost    # XGBoost only
    python train.py --model lightgbm   # LightGBM only
    python train.py --skip-smoteenn    # skip imbalance handling
"""
import argparse
import json
import numpy as np
from datetime import datetime
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, f1_score, accuracy_score,
    classification_report, confusion_matrix,
)

from utils import load_dataset, prepare_data, DATASET_PATH
from model import build_xgboost, build_lightgbm, CreditScoringModel
from edge_case_features import compute_segment_stats
from data_processing import (
    select_features_by_iv,
    apply_smoteenn,
    pca_analysis,
    calibrate_probabilities,
    compute_shap_importance,
)


def _train_and_evaluate(model, model_name, X_train, y_train, X_test, y_test, feature_columns):
    """Train a single model and return metrics."""
    print(f"\n  Training {model_name}...")
    if model_name == "lightgbm":
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)])
    else:
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    p_test = model.predict_proba(X_test)[:, 1]
    y_pred = (p_test >= 0.5).astype(int)

    auc = roc_auc_score(y_test, p_test)
    f1 = f1_score(y_test, y_pred)
    acc = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)

    print(f"    AUC:      {auc:.4f}")
    print(f"    F1:       {f1:.4f}")
    print(f"    Accuracy: {acc:.4f}")
    print(f"    TN={cm[0][0]:>6}  FP={cm[0][1]:>6}  |  FN={cm[1][0]:>6}  TP={cm[1][1]:>6}")

    return model, {"auc": auc, "f1": f1, "accuracy": acc}


def main(model_type: str = "lightgbm", skip_smoteenn: bool = False):
    print("=" * 70)
    print("  Pre-Delinquency Early Warning System — Training Pipeline")
    print("=" * 70)

    artifacts_dir = "src/model/artifacts"
    Path(artifacts_dir).mkdir(parents=True, exist_ok=True)

    # ── 1. Load dataset ──────────────────────────────────────────
    print("\n[1/8] Loading dataset...")
    df = load_dataset(DATASET_PATH)
    print(f"   Rows: {len(df):,}  |  Default rate: {df['credit_risk_label'].mean()*100:.1f}%")

    # Save segment stats for inference
    compute_segment_stats(df)

    # ── 2. Preprocess + edge case features ───────────────────────
    print("\n[2/8] Preprocessing + edge case feature engineering...")
    X, y, feature_columns, label_encoders = prepare_data(df, fit=True)
    print(f"   Features: {len(feature_columns)}")

    # ── 3. Information Value feature selection ───────────────────
    print("\n[3/8] Information Value (IV) feature selection...")
    X_selected, iv_report = select_features_by_iv(X, y, min_iv=0.02)
    selected_columns = X_selected.columns.tolist()
    print(f"   Selected: {len(selected_columns)} / {len(feature_columns)}")

    # Save IV report
    iv_report.to_csv(Path(artifacts_dir) / "iv_report.csv", index=False)

    # ── 4. Train/test split ──────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X_selected.values, y.values, test_size=0.2, random_state=42, stratify=y,
    )
    print(f"\n   Train: {len(X_train):,} | Test: {len(X_test):,}")

    # ── 5. SMOTEENN imbalance handling ───────────────────────────
    if not skip_smoteenn:
        print("\n[4/8] SMOTEENN imbalance handling...")
        X_train_balanced, y_train_balanced = apply_smoteenn(X_train, y_train)
    else:
        print("\n[4/8] SMOTEENN skipped (--skip-smoteenn)")
        X_train_balanced, y_train_balanced = X_train, y_train

    # ── 6. Train models ──────────────────────────────────────────
    print("\n[5/8] Training models...")

    results = {}

    if model_type in ("lightgbm", "both"):
        lgb, lgb_metrics = _train_and_evaluate(
            build_lightgbm(), "lightgbm",
            X_train_balanced, y_train_balanced, X_test, y_test, selected_columns
        )
        results["lightgbm"] = {"model": lgb, **lgb_metrics}

    if model_type in ("xgboost", "both"):
        xgb, xgb_metrics = _train_and_evaluate(
            build_xgboost(), "xgboost",
            X_train_balanced, y_train_balanced, X_test, y_test, selected_columns
        )
        results["xgboost"] = {"model": xgb, **xgb_metrics}

    # Pick best model by AUC
    if len(results) > 1:
        best_name = max(results, key=lambda k: results[k]["auc"])
        print(f"\n  Best model: {best_name} (AUC={results[best_name]['auc']:.4f})")
    else:
        best_name = list(results.keys())[0]

    best_model = results[best_name]["model"]
    best_metrics = {k: v for k, v in results[best_name].items() if k != "model"}

    # ── 7. Probability calibration ───────────────────────────────
    print("\n[6/8] Probability calibration (Platt scaling)...")
    calibrated_model = calibrate_probabilities(best_model, X_test, y_test, method="sigmoid")

    # Evaluate calibrated model
    cal_probs = calibrated_model.predict_proba(X_test)[:, 1]
    cal_auc = roc_auc_score(y_test, cal_probs)
    cal_y_pred = (cal_probs >= 0.5).astype(int)
    cal_f1 = f1_score(y_test, cal_y_pred)
    cal_acc = accuracy_score(y_test, cal_y_pred)
    print(f"    Calibrated AUC: {cal_auc:.4f}  F1: {cal_f1:.4f}  Acc: {cal_acc:.4f}")

    # ── 8. SHAP explainability ───────────────────────────────────
    print("\n[7/8] SHAP explainability...")
    shap_report = compute_shap_importance(
        best_model, X_test, selected_columns,
        save_path=str(Path(artifacts_dir) / "shap_explainer.joblib"),
    )

    # ── 9. PCA analysis ──────────────────────────────────────────
    print("\n[8/8] PCA variance analysis...")
    pca_report = pca_analysis(X_train, selected_columns, n_components=15)

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  FINAL RESULTS")
    print("=" * 70)

    for name, res in results.items():
        star = " ★" if name == best_name else ""
        print(f"  {name:12s}: AUC={res['auc']:.4f}  F1={res['f1']:.4f}  Acc={res['accuracy']:.4f}{star}")

    print(f"\n  Calibrated:   AUC={cal_auc:.4f}  F1={cal_f1:.4f}  Acc={cal_acc:.4f}")
    print(f"  Features:     {len(selected_columns)} (selected by IV from {len(feature_columns)})")
    print(f"  SMOTEENN:     {'Applied' if not skip_smoteenn else 'Skipped'}")
    print(f"  PCA 95% var:  {pca_report['n_components_95pct']} components")

    p_test_final = calibrated_model.predict_proba(X_test)[:, 1]
    y_pred_final = (p_test_final >= 0.5).astype(int)
    print("\n" + classification_report(y_test, y_pred_final, target_names=["No Default", "Default"]))

    # ── Save everything ──────────────────────────────────────────
    scoring_model = CreditScoringModel()
    scoring_model.model = calibrated_model  # Save calibrated version
    scoring_model.feature_columns = selected_columns
    scoring_model.label_encoders = label_encoders
    scoring_model.metadata = {
        "model_type": f"{best_name}_calibrated",
        "base_model": best_name,
        "dataset": DATASET_PATH,
        "pipeline": ["edge_case_features", "iv_selection", "smoteenn", "calibration", "shap"],
        "auc_raw": round(best_metrics["auc"], 4),
        "auc_calibrated": round(cal_auc, 4),
        "f1": round(cal_f1, 4),
        "accuracy": round(cal_acc, 4),
        "n_features_total": len(feature_columns),
        "n_features_selected": len(selected_columns),
        "iv_threshold": 0.02,
        "smoteenn_applied": not skip_smoteenn,
        "training_samples": len(X_train_balanced),
        "test_samples": len(X_test),
        "pca_components_95pct": pca_report["n_components_95pct"],
        "shap_top_features": shap_report.get("shap_ranking", {}),
        "model_comparison": {k: {kk: round(vv, 4) for kk, vv in v.items() if kk != "model"} for k, v in results.items()},
        "training_date": datetime.now().isoformat(),
    }
    scoring_model.save(artifacts_dir)

    # Save PCA report
    with open(Path(artifacts_dir) / "pca_report.json", "w") as f:
        json.dump(pca_report, f, indent=2)

    print(f"\nAll artifacts saved to {artifacts_dir}/")
    print("Done! Start the API with: uvicorn app:app --reload --port 8000")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train credit risk scoring model")
    parser.add_argument("--model", choices=["xgboost", "lightgbm", "both"], default="both",
                        help="Model to train (default: both, picks best)")
    parser.add_argument("--skip-smoteenn", action="store_true",
                        help="Skip SMOTEENN imbalance handling")
    args = parser.parse_args()
    main(model_type=args.model, skip_smoteenn=args.skip_smoteenn)

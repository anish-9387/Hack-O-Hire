"""
Advanced Data Processing Layer

Implements research-backed preprocessing techniques:
  1. Information Value (IV) — feature selection by predictive power
  2. SMOTEENN             — imbalance handling (oversample + clean noise)
  3. PCA analysis         — dimensionality reduction & variance analysis

These run BETWEEN prepare_data() and model training.
None of these modify existing code — they're additive.
"""
import numpy as np
import pandas as pd
from typing import Tuple, List


# ====================================================================
#  1. INFORMATION VALUE (IV) — Feature Selection
#     Measures each feature's predictive power for the target.
#     IV > 0.3 = Strong predictor
#     IV 0.1-0.3 = Medium
#     IV < 0.1 = Weak (candidate for removal)
# ====================================================================

def compute_woe_iv(X: pd.DataFrame, y: pd.Series, bins: int = 10) -> pd.DataFrame:
    """
    Compute Weight of Evidence (WOE) and Information Value (IV)
    for all numeric features.

    Returns DataFrame with columns: [feature, iv, strength]
    sorted by IV descending.
    """
    results = []
    for col in X.columns:
        try:
            # Bin the feature into deciles
            x = X[col].copy()
            if x.nunique() <= 2:
                binned = x.astype(str)
            else:
                binned = pd.qcut(x, q=bins, duplicates="drop").astype(str)

            df_temp = pd.DataFrame({"bin": binned, "target": y})
            grouped = df_temp.groupby("bin")["target"].agg(["sum", "count"])
            grouped.columns = ["events", "total"]
            grouped["non_events"] = grouped["total"] - grouped["events"]

            # Avoid division by zero
            total_events = grouped["events"].sum()
            total_non_events = grouped["non_events"].sum()
            if total_events == 0 or total_non_events == 0:
                results.append({"feature": col, "iv": 0, "strength": "Weak"})
                continue

            grouped["pct_events"] = grouped["events"] / total_events
            grouped["pct_non_events"] = grouped["non_events"] / total_non_events

            # Replace zeros with small number
            grouped["pct_events"] = grouped["pct_events"].replace(0, 0.0001)
            grouped["pct_non_events"] = grouped["pct_non_events"].replace(0, 0.0001)

            grouped["woe"] = np.log(grouped["pct_non_events"] / grouped["pct_events"])
            grouped["iv_component"] = (grouped["pct_non_events"] - grouped["pct_events"]) * grouped["woe"]

            iv = grouped["iv_component"].sum()

            if iv > 0.3:
                strength = "Strong"
            elif iv > 0.1:
                strength = "Medium"
            elif iv > 0.02:
                strength = "Weak"
            else:
                strength = "Negligible"

            results.append({"feature": col, "iv": round(iv, 4), "strength": strength})
        except Exception:
            results.append({"feature": col, "iv": 0, "strength": "Error"})

    iv_df = pd.DataFrame(results).sort_values("iv", ascending=False).reset_index(drop=True)
    return iv_df


def select_features_by_iv(X: pd.DataFrame, y: pd.Series, min_iv: float = 0.02) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Select features with IV above threshold.
    Returns (X_filtered, iv_report).
    """
    iv_report = compute_woe_iv(X, y)

    selected = iv_report[iv_report["iv"] >= min_iv]["feature"].tolist()
    dropped = iv_report[iv_report["iv"] < min_iv]["feature"].tolist()

    print(f"\n  Information Value Feature Selection:")
    print(f"    Total features: {len(iv_report)}")
    print(f"    Selected (IV >= {min_iv}): {len(selected)}")
    print(f"    Dropped (IV < {min_iv}): {len(dropped)}")

    # Show top 15
    print(f"\n    Top 15 by IV:")
    for _, row in iv_report.head(15).iterrows():
        print(f"      {row['feature']:45s} IV={row['iv']:.4f}  [{row['strength']}]")

    if dropped:
        print(f"\n    Dropped: {', '.join(dropped[:10])}")

    return X[selected], iv_report


# ====================================================================
#  2. SMOTEENN — Imbalance Handling
#     Combines SMOTE (oversample minority) + ENN (remove noisy samples)
#     Critical for default prediction where defaults are rare (~18%)
# ====================================================================

def apply_smoteenn(X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Apply SMOTEENN to handle class imbalance.
    Returns resampled (X, y).
    """
    try:
        from imblearn.combine import SMOTEENN
        from imblearn.over_sampling import SMOTE
        from imblearn.under_sampling import EditedNearestNeighbours

        print(f"\n  SMOTEENN Imbalance Handling:")
        print(f"    Before: {len(y)} samples, {int(y.sum())} defaults ({y.mean()*100:.1f}%)")

        smoteenn = SMOTEENN(
            smote=SMOTE(sampling_strategy=0.5, random_state=42),
            enn=EditedNearestNeighbours(sampling_strategy="majority"),
            random_state=42,
        )
        X_res, y_res = smoteenn.fit_resample(X, y)

        print(f"    After:  {len(y_res)} samples, {int(y_res.sum())} defaults ({y_res.mean()*100:.1f}%)")

        return X_res, y_res

    except ImportError:
        print("  SMOTEENN skipped: install imbalanced-learn (pip install imbalanced-learn)")
        return X, y


# ====================================================================
#  3. PCA ANALYSIS — Dimensionality Insight
#     Used for analysis/reporting, not for replacing features
#     (tree models handle high dimensionality natively)
# ====================================================================

def pca_analysis(X: np.ndarray, feature_names: List[str], n_components: int = 10) -> dict:
    """
    Run PCA for variance analysis and reporting.
    Returns dict with explained variance ratios and top components.
    """
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    # Scale first (PCA requires standardized data)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    n_components = min(n_components, X.shape[1])
    pca = PCA(n_components=n_components)
    pca.fit(X_scaled)

    cumulative_var = np.cumsum(pca.explained_variance_ratio_)

    print(f"\n  PCA Variance Analysis ({n_components} components):")
    for i in range(n_components):
        bar = "█" * int(pca.explained_variance_ratio_[i] * 50)
        print(f"    PC{i+1}: {pca.explained_variance_ratio_[i]*100:5.1f}%  cumulative: {cumulative_var[i]*100:5.1f}%  {bar}")

    # Find number of components for 95% variance
    n_95 = int(np.argmax(cumulative_var >= 0.95)) + 1
    print(f"\n    Components for 95% variance: {n_95} (out of {X.shape[1]} features)")

    # Top contributing features per component
    report = {
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "cumulative_variance": cumulative_var.tolist(),
        "n_components_95pct": n_95,
        "total_features": X.shape[1],
    }

    return report


# ====================================================================
#  4. PROBABILITY CALIBRATION
#     Raw model outputs → calibrated Probability of Default (PD)
#     Uses Platt scaling (sigmoid) or isotonic regression
# ====================================================================

def calibrate_probabilities(model, X_cal, y_cal, method: str = "sigmoid"):
    """
    Calibrate a trained model's probability outputs.
    Returns a CalibratedClassifierCV wrapper.

    Methods:
      - "sigmoid" (Platt scaling) — fast, parametric
      - "isotonic" — non-parametric, better for large datasets
    """
    from sklearn.calibration import CalibratedClassifierCV

    print(f"\n  Probability Calibration ({method}):")

    calibrated = CalibratedClassifierCV(
        model, method=method, cv="prefit"
    )
    calibrated.fit(X_cal, y_cal)

    # Compare raw vs calibrated
    raw_probs = model.predict_proba(X_cal)[:, 1]
    cal_probs = calibrated.predict_proba(X_cal)[:, 1]

    print(f"    Raw PD range:        [{raw_probs.min():.4f}, {raw_probs.max():.4f}]")
    print(f"    Calibrated PD range: [{cal_probs.min():.4f}, {cal_probs.max():.4f}]")
    print(f"    Raw PD mean:         {raw_probs.mean():.4f}")
    print(f"    Calibrated PD mean:  {cal_probs.mean():.4f}")
    print(f"    Actual default rate: {y_cal.mean():.4f}")

    return calibrated


# ====================================================================
#  5. SHAP EXPLAINABILITY
#     Feature importance + per-prediction explanations
# ====================================================================

def compute_shap_importance(model, X: np.ndarray, feature_names: List[str], save_path: str = None) -> dict:
    """
    Compute SHAP feature importance.
    Returns dict with global feature importance ranking.
    """
    try:
        import shap

        print(f"\n  SHAP Explainability:")

        # Use TreeExplainer for tree-based models
        explainer = shap.TreeExplainer(model)

        # Sample for speed (SHAP on 100K rows is slow)
        sample_size = min(5000, len(X))
        idx = np.random.choice(len(X), sample_size, replace=False)
        X_sample = X[idx]

        shap_values = explainer.shap_values(X_sample)

        # Handle multi-output
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # positive class

        # Global importance (mean absolute SHAP)
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        importance_order = np.argsort(mean_abs_shap)[::-1]

        print(f"    Top 15 features by SHAP importance:")
        shap_ranking = {}
        for i, idx_feat in enumerate(importance_order[:15]):
            name = feature_names[idx_feat]
            val = mean_abs_shap[idx_feat]
            shap_ranking[name] = round(float(val), 4)
            print(f"      {i+1:>2}. {name:45s} SHAP={val:.4f}")

        result = {
            "shap_ranking": shap_ranking,
            "explainer_type": "TreeExplainer",
            "sample_size": sample_size,
        }

        # Save explainer
        if save_path:
            import joblib
            joblib.dump(explainer, save_path)
            print(f"    Saved SHAP explainer to {save_path}")

        return result

    except ImportError:
        print("  SHAP skipped: install shap (pip install shap)")
        return {}

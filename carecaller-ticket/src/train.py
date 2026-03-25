"""Train models, tune thresholds, evaluate on validation set."""

import json
import pickle

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, classification_report
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier

from .config import OUTPUT_DIR, MODEL_DIR, TARGET
from .data_loader import load_all


def find_best_threshold(y_true, y_proba, metric="f1"):
    """Sweep thresholds to maximize F1."""
    best_thresh = 0.5
    best_score = 0.0
    for thresh in np.arange(0.05, 0.95, 0.01):
        y_pred = (y_proba >= thresh).astype(int)
        if metric == "f1":
            score = f1_score(y_true, y_pred, zero_division=0)
        elif metric == "recall":
            score = recall_score(y_true, y_pred, zero_division=0)
        else:
            score = f1_score(y_true, y_pred, zero_division=0)
        if score > best_score:
            best_score = score
            best_thresh = thresh
    return best_thresh, best_score


def train_and_evaluate():
    """Full training pipeline."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Load features
    X_train = pd.read_parquet(OUTPUT_DIR / "X_train.parquet")
    X_val = pd.read_parquet(OUTPUT_DIR / "X_val.parquet")

    # Load labels
    train_df, val_df, _ = load_all()
    y_train = train_df[TARGET].astype(int).values
    y_val = val_df[TARGET].astype(int).values

    # Align columns
    common_cols = sorted(set(X_train.columns) & set(X_val.columns))
    X_train = X_train[common_cols]
    X_val = X_val[common_cols]

    print(f"Features: {len(common_cols)}")
    print(f"Train: {X_train.shape[0]} rows, {y_train.sum()} positive ({y_train.mean():.1%})")
    print(f"Val:   {X_val.shape[0]} rows, {y_val.sum()} positive ({y_val.mean():.1%})")

    # Class imbalance weight
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos_weight = neg_count / max(pos_count, 1)
    print(f"scale_pos_weight: {scale_pos_weight:.1f}")

    # --- XGBoost ---
    print("\n--- Training XGBoost ---")
    xgb = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        eval_metric="logloss",
        random_state=42,
    )
    xgb.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    # Probabilities
    train_proba = xgb.predict_proba(X_train)[:, 1]
    val_proba = xgb.predict_proba(X_val)[:, 1]

    # Threshold tuning
    best_thresh, best_f1 = find_best_threshold(y_val, val_proba)
    print(f"\nBest threshold: {best_thresh:.2f}")
    print(f"Best val F1:    {best_f1:.4f}")

    # Detailed metrics at best threshold
    val_pred = (val_proba >= best_thresh).astype(int)
    print(f"\n--- Validation Results (threshold={best_thresh:.2f}) ---")
    print(f"F1:        {f1_score(y_val, val_pred, zero_division=0):.4f}")
    print(f"Recall:    {recall_score(y_val, val_pred, zero_division=0):.4f}")
    print(f"Precision: {precision_score(y_val, val_pred, zero_division=0):.4f}")
    print(f"Predicted: {val_pred.sum()} positive / {len(val_pred)} total")
    print(f"\n{classification_report(y_val, val_pred, target_names=['no_ticket', 'ticket'], zero_division=0)}")

    # Cross-validation on train
    print("--- 5-Fold CV on Train ---")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_f1s = []
    for fold, (tr_idx, te_idx) in enumerate(skf.split(X_train, y_train)):
        xgb_cv = XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            scale_pos_weight=scale_pos_weight, subsample=0.8,
            colsample_bytree=0.8, min_child_weight=3,
            eval_metric="logloss", random_state=42,
        )
        xgb_cv.fit(X_train.iloc[tr_idx], y_train[tr_idx], verbose=False)
        fold_proba = xgb_cv.predict_proba(X_train.iloc[te_idx])[:, 1]
        fold_pred = (fold_proba >= best_thresh).astype(int)
        fold_f1 = f1_score(y_train[te_idx], fold_pred, zero_division=0)
        cv_f1s.append(fold_f1)
        print(f"  Fold {fold + 1}: F1 = {fold_f1:.4f}")
    print(f"  Mean CV F1: {np.mean(cv_f1s):.4f} +/- {np.std(cv_f1s):.4f}")

    # Feature importance (top 20)
    importance = pd.Series(xgb.feature_importances_, index=common_cols).sort_values(ascending=False)
    print("\n--- Top 20 Features ---")
    for feat, imp in importance.head(20).items():
        print(f"  {feat}: {imp:.4f}")

    # Save model + threshold + column order
    with open(MODEL_DIR / "xgb_model.pkl", "wb") as f:
        pickle.dump(xgb, f)
    with open(MODEL_DIR / "config.json", "w") as f:
        json.dump({"threshold": best_thresh, "columns": common_cols}, f)

    print(f"\nModel saved to {MODEL_DIR}")
    return xgb, best_thresh, common_cols


def main():
    train_and_evaluate()

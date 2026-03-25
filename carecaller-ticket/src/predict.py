"""Generate predictions on the test set and output submission.csv."""

import json
import pickle

import pandas as pd

from .config import OUTPUT_DIR, MODEL_DIR
from .data_loader import load_all


def generate_submission():
    """Load model, predict on test, save submission CSV."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load model and config
    with open(MODEL_DIR / "xgb_model.pkl", "rb") as f:
        model = pickle.load(f)
    with open(MODEL_DIR / "config.json") as f:
        config = json.load(f)

    threshold = config["threshold"]
    columns = config["columns"]

    # Load test features
    X_test = pd.read_parquet(OUTPUT_DIR / "X_test.parquet")
    X_test = X_test[columns]

    # Load test call_ids
    _, _, test_df = load_all()

    # Predict
    proba = model.predict_proba(X_test)[:, 1]
    predictions = (proba >= threshold).astype(bool)

    # Build submission
    submission = pd.DataFrame({
        "call_id": test_df["call_id"].values,
        "predicted_ticket": predictions,
    })

    out_path = OUTPUT_DIR / "submission.csv"
    submission.to_csv(out_path, index=False)

    print(f"Submission saved to {out_path}")
    print(f"Threshold: {threshold:.2f}")
    print(f"Predicted tickets: {predictions.sum()} / {len(predictions)} ({predictions.mean():.1%})")

    return submission


def main():
    generate_submission()

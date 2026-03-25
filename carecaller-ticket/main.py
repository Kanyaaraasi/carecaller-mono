"""CareCaller Ticket — Call Quality Auto-Flagger

Usage:
    uv run python -m src.eda              # Exploratory data analysis
    uv run python -m src.features         # Extract features (save to outputs/)
    uv run python -m src.train            # Train model + evaluate on val
    uv run python -m src.predict          # Generate submission.csv

With LLM signals:
    GROQ_API_KEY=xxx uv run python main.py --llm

Full pipeline:
    uv run python main.py [--llm] [--nli]
"""

import argparse

from src.data_loader import load_all
from src.features import FeaturePipeline
from src.train import train_and_evaluate
from src.predict import generate_submission
from src.config import OUTPUT_DIR, TARGET


def run_pipeline(use_llm: bool = False, use_nli: bool = False,
                 llm_provider: str = "groq", llm_model: str | None = None):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    print("\n" + "=" * 60)
    print("STEP 1: Loading data")
    print("=" * 60)
    train, val, test = load_all()
    print(f"Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")

    # 2. Extract features
    print("\n" + "=" * 60)
    print("STEP 2: Extracting features")
    print("=" * 60)
    pipeline = FeaturePipeline(
        use_llm=use_llm,
        use_nli=use_nli,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )
    pipeline.fit(train)

    X_train = pipeline.transform(train, split_name="train")
    X_val = pipeline.transform(val, split_name="val")
    X_test = pipeline.transform(test, split_name="test")

    # Align columns
    common_cols = sorted(set(X_train.columns) & set(X_val.columns) & set(X_test.columns))
    X_train[common_cols].to_parquet(OUTPUT_DIR / "X_train.parquet")
    X_val[common_cols].to_parquet(OUTPUT_DIR / "X_val.parquet")
    X_test[common_cols].to_parquet(OUTPUT_DIR / "X_test.parquet")
    print(f"Saved {len(common_cols)} features to {OUTPUT_DIR}")

    # 3. Train + evaluate
    print("\n" + "=" * 60)
    print("STEP 3: Training and evaluating")
    print("=" * 60)
    train_and_evaluate()

    # 4. Generate submission
    print("\n" + "=" * 60)
    print("STEP 4: Generating submission")
    print("=" * 60)
    submission = generate_submission()

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CareCaller Ticket Auto-Flagger")
    parser.add_argument("--llm", action="store_true", help="Enable LLM-as-judge signal")
    parser.add_argument("--nli", action="store_true", help="Enable NLI contradiction checker")
    parser.add_argument("--provider", default="groq", help="LLM provider (default: groq)")
    parser.add_argument("--model", default=None, help="LLM model override")
    args = parser.parse_args()

    run_pipeline(
        use_llm=args.llm,
        use_nli=args.nli,
        llm_provider=args.provider,
        llm_model=args.model,
    )

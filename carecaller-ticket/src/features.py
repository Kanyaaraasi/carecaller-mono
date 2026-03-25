"""Combine all signal extractors into a unified feature matrix."""

import pandas as pd
import numpy as np

from .config import DROP_COLS, CATEGORICAL_COLS, TARGET
from .signals import heuristics, transcript_diff, number_checker, flow_checker
from .signals.text_features import TextFeatureExtractor
from .signals.outcome_predictor import OutcomePredictor


class FeaturePipeline:
    """Fits on train, transforms any split into a feature matrix."""

    def __init__(self, use_llm: bool = False, use_nli: bool = False,
                 llm_provider: str = "groq", llm_model: str | None = None):
        self.text_extractor = TextFeatureExtractor(max_tfidf_features=50)
        self.outcome_predictor = OutcomePredictor()
        self.use_llm = use_llm
        self.use_nli = use_nli
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self._fitted = False

    def fit(self, train_df: pd.DataFrame):
        """Fit stateful extractors on training data."""
        print("Fitting text feature extractor...")
        self.text_extractor.fit(train_df)
        print("Fitting outcome predictor...")
        self.outcome_predictor.fit(train_df)
        self._fitted = True
        return self

    def transform(self, df: pd.DataFrame, split_name: str = "") -> pd.DataFrame:
        """Extract all features from a dataframe."""
        assert self._fitted, "Must call fit() first"
        prefix = f"[{split_name}] " if split_name else ""

        # 1. Structured features (numeric + encoded categorical)
        print(f"{prefix}Extracting structured features...")
        structured = self._structured_features(df)

        # 2. Heuristic rules
        print(f"{prefix}Extracting heuristic signals...")
        heur = heuristics.extract(df)

        # 3. Transcript diff
        print(f"{prefix}Extracting transcript diff signals...")
        diff = transcript_diff.extract(df)

        # 4. Number checker
        print(f"{prefix}Extracting number checker signals...")
        nums = number_checker.extract(df)

        # 5. Flow checker
        print(f"{prefix}Extracting flow checker signals...")
        flow = flow_checker.extract(df)

        # 6. Text features (TF-IDF + keywords)
        print(f"{prefix}Extracting text features...")
        text = self.text_extractor.transform(df)

        # 7. Outcome prediction disagreement
        print(f"{prefix}Extracting outcome predictor signals...")
        outcome = self.outcome_predictor.transform(df)

        # Combine all
        all_features = pd.concat(
            [structured, heur, diff, nums, flow, text, outcome],
            axis=1,
        )

        # 8. LLM-as-judge (optional, expensive)
        if self.use_llm:
            print(f"{prefix}Running LLM-as-judge...")
            from .signals import llm_judge
            llm = llm_judge.extract(df, provider_name=self.llm_provider, model=self.llm_model)
            all_features = pd.concat([all_features, llm], axis=1)

        # 9. NLI contradiction (optional, slow)
        if self.use_nli:
            print(f"{prefix}Running NLI contradiction checker...")
            from .signals import nli_checker
            nli = nli_checker.extract(df)
            all_features = pd.concat([all_features, nli], axis=1)

        print(f"{prefix}Total features: {all_features.shape[1]}")
        return all_features

    def _structured_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract numeric + one-hot encoded categorical features."""
        # Drop leakage, text, ID columns
        cols_to_drop = [c for c in DROP_COLS if c in df.columns]
        feat = df.drop(columns=cols_to_drop, errors="ignore")

        # One-hot encode categoricals
        cat_cols = [c for c in CATEGORICAL_COLS if c in feat.columns]
        feat = pd.get_dummies(feat, columns=cat_cols, drop_first=False)

        # Convert booleans to int
        bool_cols = feat.select_dtypes(include=["bool"]).columns
        feat[bool_cols] = feat[bool_cols].astype(int)

        # Fill NaN with 0 for numeric
        feat = feat.fillna(0)

        # Ensure all columns are numeric
        feat = feat.select_dtypes(include=[np.number])

        # Derived features
        if "call_duration" in df.columns and "turn_count" in df.columns:
            feat["derived_duration_per_turn"] = (
                df["call_duration"] / df["turn_count"].replace(0, 1)
            )
        if "user_word_count" in df.columns and "agent_word_count" in df.columns:
            total_words = df["user_word_count"] + df["agent_word_count"]
            feat["derived_user_talk_ratio"] = (
                df["user_word_count"] / total_words.replace(0, 1)
            )
        if "call_duration" in df.columns and "response_completeness" in df.columns:
            feat["derived_duration_per_completeness"] = (
                df["call_duration"] / df["response_completeness"].replace(0, 0.01)
            )

        return feat


def main():
    """CLI entry point: extract features and save."""
    from .data_loader import load_all
    from .config import OUTPUT_DIR

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    train, val, test = load_all()

    pipeline = FeaturePipeline(use_llm=False, use_nli=False)
    pipeline.fit(train)

    X_train = pipeline.transform(train, split_name="train")
    X_val = pipeline.transform(val, split_name="val")
    X_test = pipeline.transform(test, split_name="test")

    # Align columns
    common_cols = sorted(set(X_train.columns) & set(X_val.columns) & set(X_test.columns))
    X_train = X_train[common_cols]
    X_val = X_val[common_cols]
    X_test = X_test[common_cols]

    X_train.to_parquet(OUTPUT_DIR / "X_train.parquet")
    X_val.to_parquet(OUTPUT_DIR / "X_val.parquet")
    X_test.to_parquet(OUTPUT_DIR / "X_test.parquet")

    print(f"\nSaved features: {len(common_cols)} columns")
    print(f"  Train: {X_train.shape}")
    print(f"  Val:   {X_val.shape}")
    print(f"  Test:  {X_test.shape}")

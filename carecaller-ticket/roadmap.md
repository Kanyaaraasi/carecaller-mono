# Problem 1: Call Quality Auto-Flagger — Roadmap

## Goal
Binary classification: predict `has_ticket` (True/False) for 159 test calls.
Scored on **F1** (primary), Recall (secondary), Precision (tertiary).
Bonus: predict ticket category.

---

## Architecture: Multi-Signal Ensemble

```
┌──────────────────────────────────────────────────────────────────┐
│                     SIGNAL EXTRACTION                            │
│                                                                  │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────────────┐ │
│  │ Structured  │ │  Transcript  │ │     LLM-as-Judge          │ │
│  │ Features    │ │  Diff (WER)  │ │  (Claude API per-call     │ │
│  │ + Heuristic │ │  whisper vs  │ │   rubric evaluation)      │ │
│  │ Rules       │ │  formatted   │ │                           │ │
│  └──────┬──────┘ └──────┬───────┘ └────────────┬──────────────┘ │
│         │               │                      │                │
│  ┌──────┴──────┐ ┌──────┴───────┐ ┌────────────┴──────────────┐ │
│  │ Conversation│ │  Number      │ │  NLI Contradiction        │ │
│  │ Flow Edit   │ │  Extraction  │ │  Scores (transcript vs    │ │
│  │ Distance    │ │  + Plausib.  │ │  structured responses)    │ │
│  └──────┬──────┘ └──────┬───────┘ └────────────┬──────────────┘ │
│         │               │                      │                │
│  ┌──────┴──────┐ ┌──────┴───────┐ ┌────────────┴──────────────┐ │
│  │ Outcome     │ │  TF-IDF on   │ │  SetFit Few-Shot on       │ │
│  │ Prediction  │ │  validation  │ │  transcript text          │ │
│  │ Disagreement│ │  _notes      │ │                           │ │
│  └──────┬──────┘ └──────┬───────┘ └────────────┬──────────────┘ │
└─────────┼───────────────┼──────────────────────┼────────────────┘
          │               │                      │
          ▼               ▼                      ▼
   ┌─────────────────────────────────────────────────────┐
   │           ALL SIGNALS → XGBoost / LightGBM          │
   │           + Threshold Tuning for max F1              │
   └─────────────────────┬───────────────────────────────┘
                         │
                         ▼
   ┌─────────────────────────────────────────────────────┐
   │         Conformal Prediction (MAPIE) for            │
   │         uncertainty quantification                  │
   └─────────────────────────────────────────────────────┘
```

---

## Phase 1: Setup & Data Loading
- [ ] Install dependencies
- [ ] Load train/val/test CSVs
- [ ] Verify shapes, columns, class balance
- [ ] Identify leakage columns to exclude

**Output:** Clean dataframes, leakage-safe column lists

---

## Phase 2: EDA & Pattern Discovery
- [ ] Profile ticket vs non-ticket (distributions of key features)
- [ ] Correlations: whisper_mismatch_count, response_completeness, outcome vs has_ticket
- [ ] Read validation_notes for ticket cases — what did the AI validator flag?
- [ ] Read a few transcript_text examples for ticket vs non-ticket calls
- [ ] Outcome × ticket cross-tab (completed:23, incomplete:16, escalated:8, opted_out:7, wrong_number:5)

**Output:** Feature hypotheses, understanding of what each issue type looks like

---

## Phase 3: Signal Extraction (the core innovation)

### 3a. Structured Features + Heuristic Rules
Standard engineered features PLUS domain-specific rules as binary flags:

| Feature | Type | Catches |
|---------|------|---------|
| call_duration, turn_count, word counts, etc. | numeric | statistical patterns |
| outcome (one-hot) | categorical | outcome-specific ticket rates |
| response_completeness | numeric | skipped questions |
| whisper_mismatch_count | numeric | STT errors |
| duration_per_turn = duration / turn_count | derived | conversation pacing anomalies |
| user_talk_ratio = user_words / total_words | derived | one-sided conversations |
| `completed` AND completeness < 0.8 | rule flag | skipped questions |
| `opted_out` AND completeness > 0.5 | rule flag | outcome miscategorization |
| `wrong_number` AND high turn_count | rule flag | wrong number misclass |

### 3b. Transcript Diff (whisper_transcript vs transcript_text)
Compare the two independent transcripts using `jiwer` and `difflib`:
- Word Error Rate (WER) between the two
- Character Error Rate (CER)
- Count of substitutions, insertions, deletions
- Max single-turn WER (worst segment)

**Why:** Directly measures STT reliability. High WER = likely audio/transcription issues.

### 3c. LLM-as-Judge (Claude API)
For each call, send transcript + responses_json + outcome to Claude with a structured rubric:

```
Evaluate this healthcare check-in call for quality issues:
1. Were all 14 required questions asked? List any missing.
2. Does the call outcome "{outcome}" match what happened in the transcript?
3. Did the agent give any medical advice or clinical recommendations?
4. Do the recorded responses match what the patient actually said?
5. Are there any STT artifacts (garbled words, impossible number values)?
6. Any other quality concerns?

Return JSON: {
  "has_issue": bool,
  "confidence": 0.0-1.0,
  "missing_questions": int,
  "outcome_mismatch": bool,
  "medical_advice_detected": bool,
  "response_data_mismatch": bool,
  "stt_artifacts": bool,
  "reasoning": "..."
}
```

This produces 6-8 binary/numeric features per call. Run on all 992 calls (~$1-5 total cost).

**Why:** Leverages world knowledge about what correct healthcare calls look like. The single most powerful signal source — can catch ALL 6 issue types.

### 3d. NLI Contradiction Detection
Use `facebook/bart-large-mnli` (free, local) to score contradictions:
- Convert each structured response → natural language hypothesis
  - e.g., response: `{"question": "current weight", "answer": "262"}` → `"The patient weighs 262 pounds"`
- Use corresponding transcript segment as premise
- NLI model outputs: entailment / contradiction / neutral probabilities
- Aggregate: max contradiction score, mean contradiction score, count of contradictions

**Why:** Purpose-built for detecting when transcript and structured data disagree.

### 3e. Number Extraction + Plausibility
Use regex + `word2number` to extract all numbers from transcript:
- Cross-reference against responses_json numeric answers (weight, age, etc.)
- Plausibility checks: weight 50-500 lbs, age 18-120
- Flag: number in response is substring of transcript number or vice versa (e.g., "62" vs "262")

**Why:** Directly catches STT mishearing on critical health values.

### 3f. Conversation Flow Edit Distance
Define expected call sequence: `[GREETING, IDENTITY, Q1-Q14, CLOSING]`
- Use keyword/regex matching to tag each agent turn with the question it's asking
- Count questions actually asked vs expected 14
- Compute sequence edit distance from ideal flow
- Features: missing_questions, out_of_order_count, repeated_questions

**Why:** Structural analysis catches skipped/reordered questions that text classifiers miss.

### 3g. Outcome Prediction Disagreement
Train a simple text classifier (TF-IDF + LogisticRegression) on transcript → outcome:
- For each call, compare predicted outcome vs labeled outcome
- Disagreement = strong flag for miscategorization
- Also use prediction entropy (low confidence = uncertain outcome)

**Why:** Self-supervision trick — learn what each outcome should look like from majority correct calls.

### 3h. TF-IDF on validation_notes
- Vectorize validation_notes (top 100-200 features)
- Extract key phrases: "mismatch", "error", "skipped", "incorrect", "medical advice", "discrepancy"
- Binary flags for issue-indicating phrases

**Why:** The post-call AI validation likely already flagged many issues — mine this signal.

### 3i. SetFit Few-Shot (optional, if time permits)
Fine-tune sentence-transformer on 59 positive transcript examples:
- Use prediction probability as an additional feature
- Trains in <1 minute, no GPU needed

---

## Phase 4: Model Training
- [ ] Combine ALL signals from Phase 3 into a single feature matrix
- [ ] Train XGBoost with `scale_pos_weight` (~10x for class imbalance)
- [ ] Also train LightGBM and CatBoost for diversity
- [ ] Stratified 5-fold CV on training set for stability
- [ ] Hyperparameter tuning: max_depth, n_estimators, learning_rate, min_child_weight

**Target:** F1 > 0.6 on validation set

---

## Phase 5: Threshold Tuning & Ensemble
- [ ] Sweep prediction thresholds 0.05-0.50 in 0.01 steps
- [ ] Pick threshold maximizing F1 on validation set
- [ ] Try blending XGBoost + LightGBM + CatBoost (simple average of probabilities)
- [ ] Analyze false negatives — what did we miss? Can we add a signal?
- [ ] Analyze false positives — what fooled us? Can we add a filter?

**Target:** F1 > 0.70 on validation set

---

## Phase 6: Conformal Prediction (bonus polish)
- [ ] Wrap final model with MAPIE for uncertainty quantification
- [ ] Identify uncertain predictions (prediction set = {True, False})
- [ ] Report: "X calls confidently flagged, Y calls uncertain"

---

## Phase 7: Bonus — Ticket Category Prediction
For calls predicted as has_ticket=True:
- Use LLM-as-judge reasoning to assign category
- Rule-based fallback: WER-based flags → audio_issue, medical advice flags → elevenlabs, outcome mismatch → openai
- Output: ticket_cat_openai, ticket_cat_elevenlabs, ticket_cat_audio_issue

---

## Phase 8: Generate Submission
- [ ] Run final pipeline on test set (159 calls)
- [ ] Output CSV: `call_id,predicted_ticket`
- [ ] Sanity check: ~9% positive rate → ~12-16 flagged calls
- [ ] Save to `carecaller-ticket/submission.csv`

---

## File Structure
```
carecaller-ticket/
├── roadmap.md              # This file
├── requirements.txt        # Python dependencies
├── config.py               # Paths, constants, leakage columns
├── data_loader.py          # Load and clean data
├── eda.py                  # Exploratory data analysis
├── signals/
│   ├── heuristics.py       # Rule-based flags
│   ├── transcript_diff.py  # WER between whisper and formatted transcripts
│   ├── llm_judge.py        # Claude API evaluation per call
│   ├── nli_checker.py      # NLI contradiction detection
│   ├── number_checker.py   # Numeric extraction + plausibility
│   ├── flow_checker.py     # Conversation flow edit distance
│   ├── outcome_predictor.py# Outcome disagreement detector
│   └── text_features.py    # TF-IDF on validation_notes
├── features.py             # Combine all signals into feature matrix
├── train.py                # Model training + CV + threshold tuning
├── predict.py              # Generate test predictions
├── evaluate.py             # Metrics reporting
├── submission.csv          # Final output
└── models/                 # Saved model artifacts
```

---

## Dependencies
```
pandas
numpy
scikit-learn
xgboost
lightgbm
jiwer                      # transcript WER comparison
word2number                 # number extraction from text
transformers               # NLI model (bart-large-mnli)
torch                      # backend for transformers
anthropic                  # Claude API for LLM-as-judge
mapie                      # conformal prediction
```

---

## Execution Order (what to build first)

Priority is based on expected signal strength and build speed:

| Priority | Signal | Expected Impact | Build Time |
|----------|--------|----------------|------------|
| 1 | Structured features + heuristic rules | Medium | 30 min |
| 2 | LLM-as-Judge (Claude API) | **Very High** | 45 min |
| 3 | TF-IDF on validation_notes | High | 15 min |
| 4 | Transcript diff (WER) | High | 20 min |
| 5 | Number extraction + plausibility | Medium-High | 20 min |
| 6 | Conversation flow edit distance | Medium | 30 min |
| 7 | NLI contradiction scores | Medium | 30 min |
| 8 | Outcome prediction disagreement | Medium | 20 min |
| 9 | XGBoost training + threshold tuning | **Critical** | 30 min |
| 10 | Ensemble + conformal prediction | Low-Medium | 20 min |

**Total estimated effort: ~4-5 hours for full pipeline**

---

## Data Leakage Warning
**DO NOT use as features:**
- `has_ticket` (target)
- `ticket_initial_notes`, `ticket_resolution_notes` (only exist for ticket cases)
- `ticket_priority`, `ticket_status`, `ticket_has_reason`
- `ticket_cat_*` columns (these ARE the labels)
- `ticket_raised_at`, `ticket_resolved_at`

These are empty in the test set and would cause leakage in training.

---

## Key Risks & Mitigations
| Risk | Mitigation |
|------|-----------|
| Only 59 positive train examples | Class weights + diverse signals reduce overfitting to any single pattern |
| LLM-as-judge inconsistency | Run twice, average scores; use structured JSON output |
| Overfitting to validation set | 5-fold CV on train; val is final sanity check only |
| NLI model too slow | Batch inference; only run on relevant transcript segments |
| Threshold sensitivity | Fine-grained sweep; report F1 curve |
| Too many features for 689 samples | Feature selection via importance; regularization |

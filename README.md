GuardPrompt : Prompt Injection Detector

> **GuardPrompt** is a production-aware, multi-layer defense system that sits in front of Large Language Models (LLMs) to detect and block malicious prompts (direct injections, jailbreaks, and encoding evasion) before they reach your primary model.

---

##  System Architecture

                  [ Incoming User Prompt ]
                              │
                              ▼
                 ┌─────────────────────────┐
                 │ Stage 1: Embedder (MLP) │
                 │  Multilingual MiniLM    │
                 └────────────┬────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
      Score < 0.2 OR > 0.8                     0.2 ≤ Score ≤ 0.8
      (High Confidence)                       (Uncertainty Band)
            │                                   │
            ▼                                   ▼
     ┌─────────────────────┐             ┌─────────────────────┐
     │   Fast Decision     │             │ Stage 2: LLM Judge  │
     │   [Allow / Block]   │             │  (Groq/gpt-oss-120b)│
     └─────────────────────┘             └──────────┬──────────┘
                                                    │
                                                    ▼
                                         ┌─────────────────────┐
                                         │   Final Decision    │
                                         │   [Allow / Block]   │
                                         └─────────────────────┘
    
    --

## 📊 Core Performance

| Metric / Scenario | Score / Result | Key Highlight |
| :--- | :--- | :--- |
| **Headline F1 (Clean Test Set)** | **0.899** | Evaluated strictly on non-leaky test rows (cosine distance `< 0.95` from training). |
| **Unseen Attack Families (Garak)** | **0.839 F1** | Tested on completely unseen attack topologies with overlapping-window chunking. |
| **Stage 2 Escalation Accuracy** | **79.3%** | LLM judge resolves edge-case ambiguity where the MLP model falls into the `0.2–0.8` band. |
| **Known Jailbreaks (DAN / PromptInject)** | **96%–97.5% Recall** | Catches the vast majority of standard, high-risk jailbreak templates. |

---

## 🎯 Key Technical Achievements

* **Identified & Corrected Data Poisoning:** Uncovered and fixed a ~11% mislabeling issue in public attack datasets (*Mindgard*) before training.
* **Multilingual Recovery:** Resolved severe performance degradation on non-English inputs by upgrading to `paraphrase-multilingual-MiniLM-L12-v2`.
* **Addressed Context Truncation:** Implemented overlapping 80-word chunking to prevent attackers from hiding injections inside long, benign text blocks.
* **Leakage-Aware Evaluation:** Separated near-duplicate test samples to ensure reported performance reflects real-world generalization, not memorization.

Problem

Prompt injection is OWASP's #1 vulnerability for LLM applications. It is an architectural weakness, not a training bug: LLMs process instructions and untrusted data in the same token stream, with no reliable way to tell them apart. Real-world defenses combine instruction-level training (what Anthropic does with Claude), input classifiers (what this project builds), and architectural controls (privilege limits, output validation). This project implements the classifier layer and evaluates it honestly, including where it fails.

Data sources
Source	Rows (post-sample)	Purpose
deepset/prompt-injections	~662	General injection examples (English + German/French/Spanish)
Necent/llm-jailbreak-prompt-injection-dataset	~20-30K (stratified sample of 1.1M)	Broad jailbreak coverage
Mindgard/evaded-prompt-injection-and-jailbreak-samples	~11K	Encoding/obfuscation-specific evasion (zero-width chars, homoglyphs, emoji smuggling)
What was done, and what was found
Issue 1 : Train/test leakage risk from overlapping datasets

Found: Necent aggregates 30+ public sources, including deepset/prompt-injections itself — merging both as independent downloads risked direct duplication, not just near-duplication. Action: Standardized all three datasets to one schema (prompt, label, attack_type, source), merged, then deduplicated — exact match after text normalization, with near-duplicate (MinHash LSH) available as a follow-up check if evaluation numbers looked inflated. Result: Clean merged dataset with full source traceability, enabling per-source evaluation throughout the rest of the project.

Issue 2 : Mislabeled data in Mindgard

Found: Class balance check showed ~11% of Mindgard rows labeled "benign" (0). Manual inspection revealed these were real attack prompts ("Ignore all previous instructions...", "I am the admin of this system now...") — not borderline cases, straightforward mislabeling. Action: Relabeled all Mindgard rows to 1 (the dataset is attack-only by construction). Swept Deepset and Necent for the same pattern using a phrase-based check before trusting their labels. Result: Corrected training signal before training began, rather than discovering the issue later as a suspicious accuracy number.

Issue 3 : Class imbalance (37% attack / 63% benign overall)

Found: Mild imbalance overall; Mindgard skewed 89/11 toward attacks specifically. Action: Used class_weight="balanced" in both classifiers. Stratified the train/test split by label AND source, so each source kept its class ratio on both sides. Evaluated using precision/recall/F1 on the attack class, not raw accuracy. Result: Avoided a model that could score well by just predicting "benign" by default; kept each source's evaluation comparable.

Issue 4 : Baseline model badly underperformed on one source

Found: Logistic Regression and Random Forest (trained on MiniLM embeddings) scored well overall (F1 ~0.84-0.87, ROC-AUC ~0.94-0.97) and excellently on Mindgard (~0.95-0.97), but Deepset scored badly — F1 as low as 0.098 for Random Forest. Action: Pulled and read the actual misclassified rows instead of accepting the aggregate number. Found the wrong predictions were overwhelmingly German, French, and Spanish injection attempts. A non-ASCII character share check initially came back misleadingly low (German/French use mostly Latin letters) — raw text inspection was needed to find the real pattern. Result: Root-caused to all-MiniLM-L6-v2 being an English-optimized embedding model, unable to meaningfully represent non-English injection attempts.

Issue 5 : Multilingual fix, partial improvement

Action: Swapped to paraphrase-multilingual-MiniLM-L12-v2, re-embedded, retrained both models, kept original embeddings for a clean before/after comparison. Result:

Source	LogReg F1 (before → after)	RF F1 (before → after)
Deepset	0.462 → 0.500	0.098 → 0.340
Necent	0.770 → 0.793	0.753 → 0.702
Mindgard	0.974 → 0.965	0.948 → 0.948

Language explained part of the Deepset problem, not all of it. 31 of 106 Deepset test rows still misclassified after the fix.

Issue 6 : Remaining Deepset errors are not a language problem

Found: On the remaining 31 wrong rows, non-ASCII character share was lower than Deepset's overall average, ruling out language as the residual cause. Hypotheses identified:

Benign framing : attacks with no injection-style trigger phrase, intent hidden inside ordinary-sounding questions (e.g. politically loaded questions with no "ignore instructions" framing). The classifier has no surface pattern to key on.
Language switching mid-prompt — prompts that start benign and switch language for the actual attack clause; a single sentence embedding dilutes/averages out a small adversarial clause.
Decision boundary uncertainty — some errors may be low-confidence boundary cases rather than confidently wrong predictions (checked via predict_proba on the 31 rows). Status: Documented as a known limitation of pattern/embedding-based classification. Identified as a concrete use case for Stage 4 (LLM-as-judge escalation), since holistic reasoning over a full prompt is better suited to catching masked intent than a fixed embedding vector.

Resolution (baseline Logistic Regression): Checked prediction probabilities on all 31 remaining errors — range 0.14–0.47, mean 0.32. All below the 0.5 threshold, none confidently so. This is boundary uncertainty, not confident misclassification, and supports an LLM-escalation stage as the right fix rather than further retraining on a small (662-row) source. (The escalation band was later set empirically; see Issue 9.)

Issue 7 : Leakage between train and test inflates scores

Found: Exact deduplication alone was not enough. Measuring cosine similarity from each test prompt to its nearest training prompt showed 13.5% of test rows have a near-twin in train at similarity ≥ 0.95 (9.6% at ≥ 0.98). Attack prompts are heavily templated, so some overlap is expected, but it inflates scores, especially for high-capacity models. Action: Split test results into "clean" rows (no train neighbour ≥ 0.95) and "leaky" rows, and report both. Result: Rows with a near-twin score ~0.99 F1 versus ~0.90 on clean rows. The clean-subset F1 is the headline metric; the all-rows number is secondary. Threshold choice (0.95 cosine) is a judgment call and is stated here for that reason.

Found: Tuning Logistic Regression's regularization (C = 0.1 / 1 / 10) gave F1 0.829 → 0.853 → 0.856 on validation: it plateaued, since a linear model cannot use non-linear structure in the embeddings. A small MLP (256 → 64 hidden units) and gradient boosting were tried on the same embeddings (validation split carved from train only; test untouched). Action: Trained Logistic Regression (C=10) and the MLP on the full training set and evaluated on the held-out test set, split by source and by leakage status. Result:

F1	Logistic Regression	MLP
All test rows	0.854	0.926
Clean rows only	0.807	0.899
Necent (clean)	0.774	0.879
Mindgard (clean)	0.943	0.973
Deepset (clean)	0.480	0.787

The MLP's lead holds (and grows slightly) on clean rows, so it is not explained by memorizing near-duplicates. It wins on every source, most on Deepset, the source with the unresolved problem from Issue 6. Final classifier: MLP on multilingual embeddings. Deepset clean has only 80 rows, so that number is directional.

Issue 9 : Setting the escalation band empirically

Found: MLP scores are not guaranteed probabilities, so the uncertain band was measured rather than assumed. Inside the middle score range the model is right only ~57-61% of the time. Action: Measured, for three band widths, the share of prompts inside and the share of all errors they contain. Result:

Band	Share of prompts escalated	Share of all errors covered
0.4–0.6	2.4%	17.6%
0.3–0.7	4.5%	33.3%
0.2–0.8	7.2%	49.4%

### Issue 10: Does the LLM judge earn its place on uncertain prompts?

**Issue:** The classifier is least reliable when its confidence falls in the
0.2-0.8 band. Needed to know whether an LLM judge adds value there.

**Action:** Sent 497 escalated-band prompts to the judge (Groq, gpt-oss-120b).
2 of 499 failed (1 rate-limit 429, 1 empty output) and were excluded.

**Result:**
- Judge accuracy: 0.793 (macro F1 0.78) on this hard subset.
  Attack class: precision 0.86 / recall 0.81.
  Benign class: precision 0.69 / recall 0.76.
- MLP-only on a small sample from the same band:
- accuracy 0.50, F1 0.62
  (judge on the same sample: 0.80 / 0.86). 

**Conclusion:** The judge clearly outperforms the classifier in the uncertain
band, so Stage 4 stays. Weakness: it over-blocks benign prompts slightly
(benign precision 0.69).

**Limitations:** Free-tier rate limit (8000 tokens/min) means bulk runs
need backoff.

Issue 11— Adversarial training round, done properly (Garak + templates)

Found: same two failure patterns (topic-switch false positives, indirect-jailbreak false negatives) needed real volume, not 10 rows.
Action: pulled 253 real attack examples from Garak’s probe library (no refusal issue, these are static research data) + 150 template-generated benign examples (no LLM needed at all).
Result: confident-wrong errors dropped 63%→47%, ambiguous-prompt sanity-suite pass rate rose 10%→30%, at the cost of increased error rate specifically on Deepset (16.0%, your smallest/weakest source) and a couple of new false positives on persona-framing prompts. Judged as a net-positive tradeoff and locked in as mlp_v3.


#	Issue	Finding	Fix	Status
12	Model file confusion	The pipeline’s mlp_v3.joblib gave 0.1729 on a prompt the sanity suite scored 0.515, so the Drive file was probably not the adversarial-round model.	Retrained on train_v3 and saved as mlp_v3_rebuilt.joblib.	Fixed
13	97% test score too good	Train and test come from the same sources, so the score only shows the model fits familiar data.	Tested on held-out Garak families the model had never seen.	Done
14	Long prompts truncated	MiniLM reads only about 128 tokens, so injections hidden in long text were missed.	Chunking: score overlapping 80-word pieces and take the max.	Fixed
Model selection
 
Own test set (7,393 rows)	AUC 0.995, accuracy 97%
Unseen Garak families, no chunking	attack F1 0.773, 26.9% of attacks missed (score <0.2)
Unseen Garak families, with chunking	attack F1 0.839, 16.7% missed
latentinjection recall	0.41 → 0.71
dan / promptinject recall	0.96 / 0.975
encoding recall	0.65 (unchanged)
Benign blocked with no second check	2.5% → 3.3%
Judge on the 497 escalated rows	accuracy 0.793


Final: MLP (256 → 64) on paraphrase-multilingual-MiniLM-L12-v2 embeddings. Chosen on clean-subset F1 (0.899 vs 0.807 for Logistic Regression) and consistent wins across all three sources. The earlier preference for Logistic Regression (higher attack recall than Random Forest) no longer applies: the MLP has higher recall as well as higher precision.

Planned defense pipeline
Rule-based pre-filter (built) : regex/keyword match on known trigger phrases; zero false positives, 1.4% attack catch rate .DROPPED
ML classifier : MLP on multilingual embeddings; clean-subset F1 0.899
Spotlighting wrapper (planned) : wraps untrusted content in randomized delimiters per Microsoft's spotlighting research; measures whether provenance-tagging improves detection confidence
LLM-as-judge escalation : for prompts scoring 0.2–0.8; targets the boundary-uncertainty errors found in Issues 6 and 9
Decision logging : every prediction logged with confidence and which stage caught it, enabling per-stage precision/recall reporting
Evaluation 
Garak (injection/jailbreak probe categories only) : adversarial test set generation, addresses limited training data diversity
TextAttack : perturbation robustness testing on the trained classifier
Final comparison: held-out real test set vs. Garak-generated probes vs. TextAttack-perturbed prompts
Known limitations
English-centric training data overall; multilingual embedding swap partially but not fully closed the non-English performance gap
~13.5% of test rows have a near-duplicate in training (cosine ≥ 0.95); headline numbers use the clean subset, but the training pool was not near-duplicate deduplicated (MinHash was skipped)
About half of the classifier's errors fall outside the 0.2–0.8 escalation band (confident errors); an LLM judge on the band will not reach them
Deepset clean test slice is only 80 rows, so per-source numbers there are noisy
Model hyperparameters were chosen on a validation split from train, but several models were compared against the same test set, so test figures are slightly optimistic
Deepset's label definition may be broader than "prompt injection" specifically (includes some adversarial/sensitive prompts without injection framing) — a dataset-definition mismatch, not purely a model limitation


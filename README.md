GuardPrompt : Prompt Injection Detection

A classifier that sits in front of an LLM and flags malicious prompts (direct injection, jailbreaks, and encoding-based evasion) before they reach the model. Built as one layer of a defense-in-depth system, not a standalone solution — no detector, including production tools from Anthropic and OpenAI, claims full coverage against prompt injection.

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

Chosen band: 0.2–0.8 : about 7% of traffic sent for a second opinion covers roughly half of the classifier's mistakes. The other half are confident errors that no threshold fixes; documented as a limitation.

Stage 1 (rules) evaluated on its own

Regex trigger-phrase filter: 0 false positives on 4,329 benign test prompts, but catches only 39 of 2,781 attacks (1.4%). Precise but narrow; a cheap safety net, not a major contributor.

Model selection

Final: MLP (256 → 64) on paraphrase-multilingual-MiniLM-L12-v2 embeddings. Chosen on clean-subset F1 (0.899 vs 0.807 for Logistic Regression) and consistent wins across all three sources. The earlier preference for Logistic Regression (higher attack recall than Random Forest) no longer applies: the MLP has higher recall as well as higher precision.

Planned defense pipeline (in progress)
Rule-based pre-filter (built) : regex/keyword match on known trigger phrases; zero false positives, 1.4% attack catch rate (see above)
ML classifier (built) : MLP on multilingual embeddings; clean-subset F1 0.899
Spotlighting wrapper (planned) : wraps untrusted content in randomized delimiters per Microsoft's spotlighting research; measures whether provenance-tagging improves detection confidence
LLM-as-judge escalation (next) : for prompts scoring 0.2–0.8; targets the boundary-uncertainty errors found in Issues 6 and 9
Decision logging : every prediction logged with confidence and which stage caught it, enabling per-stage precision/recall reporting
Planned evaluation (not yet run)
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
Rule-based pre-filter (Stage 1) is English-only; non-English equivalents of trigger phrases are not yet covered
No full RL training (as used in Anthropic's production defenses) out of scope for this project's compute budget; an adversarial training loop is planned as a smaller-scale analog

# GuardPrompt : Prompt Injection Detection

A classifier that sits in front of an LLM and flags malicious prompts (direct injection, jailbreaks, and encoding-based evasion) before they reach the model. Built as one layer of a defense-in-depth system, not a standalone solution — no detector, including production tools from Anthropic and OpenAI, claims full coverage against prompt injection.

## Problem

Prompt injection is OWASP's #1 vulnerability for LLM applications. It is an architectural weakness, not a training bug: LLMs process instructions and untrusted data in the same token stream, with no reliable way to tell them apart. Real-world defenses combine instruction-level training (what Anthropic does with Claude), input classifiers (what this project builds), and architectural controls (privilege limits, output validation). This project implements the classifier layer and evaluates it honestly, including where it fails.

## Data sources

| Source | Rows (post-sample) | Purpose |
|---|---|---|
| `deepset/prompt-injections` | ~662 | General injection examples (English + German/French/Spanish) |
| `Necent/llm-jailbreak-prompt-injection-dataset` | ~20-30K (stratified sample of 1.1M) | Broad jailbreak coverage |
| `Mindgard/evaded-prompt-injection-and-jailbreak-samples` | ~11K | Encoding/obfuscation-specific evasion (zero-width chars, homoglyphs, emoji smuggling) |

## What was done, and what was found

### Issue 1 : Train/test leakage risk from overlapping datasets
**Found:** Necent aggregates 30+ public sources, including `deepset/prompt-injections` itself. merging both as independent downloads risked direct duplication, not just near-duplication.
**Action:** Standardized all three datasets to one schema (`prompt, label, attack_type, source`), merged, then deduplicated exact match after text normalization, with near-duplicate (MinHash LSH) available as a follow-up check if evaluation numbers looked inflated.
**Result:** Clean merged dataset with full source traceability, enabling per-source evaluation throughout the rest of the project.

### Issue 2 : Mislabeled data in Mindgard
**Found:** Class balance check showed ~11% of Mindgard rows labeled "benign" (0). Manual inspection revealed these were real attack prompts ("Ignore all previous instructions...", "I am the admin of this system now...")  not borderline cases, straightforward mislabeling.
**Action:** Relabeled all Mindgard rows to 1 (the dataset is attack-only by construction). Swept Deepset and Necent for the same pattern using a phrase-based check before trusting their labels.
**Result:** Corrected training signal before training began, rather than discovering the issue later as a suspicious accuracy number.

### Issue 3 : Class imbalance (37% attack / 63% benign overall)
**Found:** Mild imbalance overall; Mindgard skewed 89/11 toward attacks specifically.
**Action:** Used `class_weight="balanced"` in both classifiers. Stratified the train/test split by label AND source, so each source kept its class ratio on both sides. Evaluated using precision/recall/F1 on the attack class, not raw accuracy.
**Result:** Avoided a model that could score well by just predicting "benign" by default; kept each source's evaluation comparable.

### Issue 4 : Baseline model badly underperformed on one source
**Found:** Logistic Regression and Random Forest (trained on MiniLM embeddings) scored well overall (F1 ~0.84-0.87, ROC-AUC ~0.94-0.97) and excellently on Mindgard (~0.95-0.97), but Deepset scored badly F1 as low as 0.098 for Random Forest.
**Action:** Pulled and read the actual misclassified rows instead of accepting the aggregate number. Found the wrong predictions were overwhelmingly German, French, and Spanish injection attempts. A non-ASCII character share check initially came back misleadingly low (German/French use mostly Latin letters) raw text inspection was needed to find the real pattern.
**Result:** Root-caused to `all-MiniLM-L6-v2` being an English-optimized embedding model, unable to meaningfully represent non-English injection attempts.

### Issue 5 : Multilingual fix, partial improvement
**Action:** Swapped to `paraphrase-multilingual-MiniLM-L12-v2`, re-embedded, retrained both models, kept original embeddings for a clean before/after comparison.
**Result:**

| Source | LogReg F1 (before → after) | RF F1 (before → after) |
|---|---|---|
| Deepset | 0.462 → 0.500 | 0.098 → 0.340 |
| Necent | 0.770 → 0.793 | 0.753 → 0.702 |
| Mindgard | 0.974 → 0.965 | 0.948 → 0.948 |

Language explained part of the Deepset problem, not all of it. 31 of 106 Deepset test rows still misclassified after the fix.

### Issue 6 : Remaining Deepset errors are not a language problem
**Found:** On the remaining 31 wrong rows, non-ASCII character share was *lower* than Deepset's overall average, ruling out language as the residual cause.
**Hypotheses identified:**
1. **Benign framing**  attacks with no injection-style trigger phrase, intent hidden inside ordinary-sounding questions (e.g. politically loaded questions with no "ignore instructions" framing). The classifier has no surface pattern to key on.
2. **Language switching mid-prompt**  prompts that start benign and switch language for the actual attack clause; a single sentence embedding dilutes/averages out a small adversarial clause.
3. **Decision boundary uncertainty** some errors may be low-confidence boundary cases rather than confidently wrong predictions (checked via `predict_proba` on the 31 rows).
**Status:** Documented as a known limitation of pattern/embedding-based classification. Identified as a concrete use case for Stage 4 (LLM-as-judge escalation), since holistic reasoning over a full prompt is better suited to catching masked intent than a fixed embedding vector.

resolution : Checked prediction probabilities on all 31 remaining errors — range 0.14–0.47, mean 0.32. All below the 0.5 threshold, none confidently so. This is boundary uncertainty, not confident misclassification, and supports Stage 4 (LLM-escalation at 0.4–0.6 confidence) as the right fix rather than further retraining on a small (662-row) source.

## Model selection

**Logistic Regression**, on multilingual embeddings, chosen over Random Forest despite Random Forest's marginally higher ROC-AUC : Logistic Regression has better recall on the attack class (0.90 vs 0.72), and in a security context a missed attack (false negative) is costlier than a false alarm.

## Planned defense pipeline

1. **Rule-based pre-filter** : regex/keyword match on known trigger phrases, catches obvious attacks before the ML model runs
2. **ML classifier** (built, evaluated above) : semantic detection for paraphrased/reworded attacks
3. **Spotlighting wrapper** : wraps untrusted content in randomized delimiters per Microsoft's spotlighting research; measures whether provenance-tagging improves detection confidence
4. **LLM-as-judge escalation** : for uncertain classifier confidence (0.4-0.6) or suspected benign-framing cases; targeted follow-up for Issue 6
5. **Decision logging** : every prediction logged with confidence and which stage caught it, enabling per-stage precision/recall reporting

## Planned evaluation 

- **Garak** (injection/jailbreak probe categories only) : adversarial test set generation, addresses limited training data diversity
- **TextAttack** : perturbation robustness testing on the trained classifier
- Final comparison: held-out real test set vs. Garak-generated probes vs. TextAttack-perturbed prompts

## Known limitations

- English-centric training data overall; multilingual embedding swap partially but not fully closed the non-English performance gap
- Deepset's label definition may be broader than "prompt injection" specifically (includes some adversarial/sensitive prompts without injection framing) : a dataset-definition mismatch, not purely a model limitation
- Rule-based pre-filter (Stage 1) is English-only; non-English equivalents of trigger phrases are not yet covered
- No full RL training (as used in Anthropic's production defenses) : out of scope for this project's compute budget; an adversarial training loop is planned as a smaller-scale analog

# TASK: Close WHO Validation Gate and Freeze the Final Tabular Experiment Pipeline for Tunas

You are working directly inside the **Tunas / tunas-posyandu** repository for the Datathon 2026 semifinal.

Your goal in this task is to make the existing WHO growth-standard and tabular ML pipeline **scientifically defensible, reproducible, fully tested, and ready for final experiments**.

This is a high-stakes competition repository with an imminent deadline. Work carefully and verify every change. Do not optimize for the appearance of progress. Optimize for correctness, reproducibility, and evidence.

---

# 1. Primary Objective

Complete these two dependent workstreams, in order:

1. **Close the official WHO validation gate**
2. **Freeze and execute the final tabular evaluation pipeline**

Do not work on frontend, backend API, paper writing, CV implementation, Hugging Face upload, or unrelated cleanup in this task.

---

# 2. Repository-First Rule

Before changing anything:

1. Inspect the repository structure.
2. Read the existing documentation relevant to:
   - WHO LMS / HAZ calculation
   - synthetic cohort generation
   - target definition
   - feature engineering
   - train/validation/test splitting
   - baselines
   - LightGBM models
   - capacity-constrained ranking
   - SHAP
   - model persistence
   - tests
   - existing experiment scripts/configuration
3. Inspect Git status and current HEAD.
4. Run the existing test suite and record the baseline result.
5. Identify exactly why any tests are skipped or failing.

Treat the **current implementation and decision documents in the repository as the source of truth**.

Do not blindly trust README claims if they disagree with the actual code.

Do not redesign working components without evidence that they are wrong.

---

# 3. Known Starting Context

The latest repository was previously observed to have approximately:

- 204 passing tests
- 4 skipped tests

The skipped tests were believed to be related to external/official WHO validation data.

The expected WHO data path may include something similar to:

`data/who/lhfa_lms.csv`

but **do not assume this path or schema is correct without inspecting the repository**.

The existing tabular system already includes or is expected to include:

- synthetic longitudinal Posyandu cohorts
- WHO HAZ computation
- snapshot features
- trajectory features
- contextual features
- child-grouped splitting
- temporal evaluation / label-maturity safeguards
- B0 / B1 / B2 baselines
- M1 / M2 / M3 model variants
- LightGBM
- exact capacity-constrained ranking
- Recall@K
- Precision@K
- Lift@K
- AUPRC
- SHAP explanations
- model persistence

**M2 is the pre-specified primary model.**

Do not choose another primary model because it performs better on the final test data.

The current target is prospective growth deterioration rather than merely reproducing the current WHO stunting threshold. Preserve the existing target specification and its current decision record. Do not silently redefine it.

---

# 4. Workstream A: Close Official WHO Validation

## 4.1 Inspect the Current WHO Implementation

Locate and understand:

- WHO LMS lookup code
- age handling
- sex handling
- length vs height handling
- interpolation behavior, if any
- out-of-range behavior
- HAZ calculation
- reference-case tests
- external-data tests
- synthetic generator dependencies on WHO data

Before editing, determine:

1. what data format the code expects,
2. which WHO standard is intended,
3. which tests are currently skipped,
4. whether any test currently validates against an independent official reference.

---

## 4.2 Obtain Official WHO Reference Data Safely

If network access is available:

- obtain the required WHO Child Growth Standards reference data from an **official WHO source**;
- prefer the exact official table/file relevant to length/height-for-age for the supported age range;
- do not use Kaggle mirrors, random GitHub repositories, blog posts, or manually reconstructed values when an official WHO source is available;
- record provenance clearly.

If the official WHO source provides a different schema from the repository's expected schema:

- write a deterministic conversion/import step;
- preserve the raw official source separately when practical;
- document exactly how the normalized file was produced;
- do not manually copy hundreds of values.

If network access is unavailable:

- do not fabricate the WHO table;
- complete all code/test/integration work that does not require the external file;
- make the missing external artifact explicit in the final report;
- leave a deterministic importer/downloader or clearly documented placement workflow ready for the user.

Do not claim the WHO gate is closed unless independent official-reference validation actually passes.

---

## 4.3 Add Provenance

For any official WHO artifact added or normalized, preserve enough information to reproduce it.

At minimum record:

- source organization
- source document/file name
- source URL if available
- retrieval date
- transformation performed, if any
- relevant age/sex/indicator scope

Prefer a small machine-readable metadata file or an existing repository convention.

Do not include secrets or local machine paths.

---

## 4.4 Validate Against Independent Reference Cases

The WHO implementation must not only test itself against values generated by itself.

Create or complete tests using **independent official WHO reference values**.

Test representative cases covering, where supported:

- male / female
- multiple ages
- near the lower age boundary
- near the upper supported age boundary
- median-like measurements
- measurements producing negative HAZ
- measurements producing positive HAZ
- threshold-near cases around HAZ = -2 where practical

Use tolerances justified by the official source precision.

Do not relax tolerances merely to make tests pass.

If discrepancies appear, investigate the implementation or data transformation instead.

---

## 4.5 WHO Definition of Done

The WHO workstream is complete only when:

- official reference data provenance is documented;
- all expected WHO data can be loaded reproducibly;
- independent official reference cases pass;
- synthetic generation can consume the WHO implementation from a clean environment;
- WHO-related tests no longer skip merely because repository-required official data is absent;
- no regression is introduced elsewhere.

Run the relevant focused tests first, then the full test suite.

---

# 5. Workstream B: Freeze the Final Tabular Experiment Pipeline

Only start this after the WHO implementation is sufficiently validated.

The objective is **not to invent a better model**.

The objective is to produce the final, reproducible evidence needed to evaluate the already-designed system.

---

## 5.1 Preserve Scientific Decisions

Do not change, unless the current code is demonstrably broken:

- target definition
- horizon definition
- train/test semantics
- child-level evaluation unit
- grouped split semantics
- temporal label-maturity logic
- feature-family definitions
- baseline definitions
- M1/M2/M3 definitions
- primary-model designation
- capacity-ranking semantics
- SHAP semantics

If you discover a scientific or leakage bug:

1. verify it with a minimal reproducible example or test;
2. fix it;
3. add a regression test;
4. explain the impact on previous results.

Never silently change experiment semantics.

---

# 6. Final Experiment Requirements

Build or harden one canonical experiment runner that can reproduce the final tabular evaluation from configuration.

Prefer extending existing code rather than creating a parallel framework.

The final suite should evaluate:

### Baselines
- B0
- B1
- B2

### Model variants
- M1
- M2
- M3

with **M2 remaining the primary model regardless of final test performance**.

---

# 7. Evaluation Protocol

Preserve the repository's established grouped and temporal evaluation semantics.

At minimum report, where applicable:

- AUPRC
- Recall@K
- Precision@K
- Lift@K

Use exact-K selection.

Do not implement threshold logic that can return more than K children because of score ties.

Tie-breaking must be deterministic and documented.

Do not rerank independently inside demographic/error-analysis slices when the intended question concerns the global operational ranking.

---

# 8. Multi-Seed Robustness

The final evidence must not rely on one lucky synthetic cohort.

Run the complete final experiment over:

- **5 generator/random seeds if computationally practical**
- otherwise a **minimum of 3 seeds**

Use deterministic, explicitly recorded seeds.

Aggregate metrics as:

`mean ± standard deviation`

for every important model/evaluation/metric combination.

Do not cherry-pick the best seed.

Save the per-seed raw metrics as well as the aggregate summary.

If runtime makes 5 seeds unreasonable, use 3 and document the reason. Do not reduce below 3.

---

# 9. Required Ablation Evidence

Use the existing feature/model definitions to produce a clean ablation showing the incremental role of feature families.

At minimum, if these correspond to the existing M1/M2/M3 semantics, quantify:

- snapshot-only information
- snapshot + trajectory information
- snapshot + trajectory + contextual information

Do not redefine M1/M2/M3 just to fit this wording. First inspect their actual definitions.

The final result must make it possible to answer:

> Does longitudinal trajectory information add useful ranking signal beyond a current snapshot in the controlled synthetic environment?

Phrase interpretation conservatively.

Because the data are synthetic, do **not** infer external clinical effectiveness from these experiments.

---

# 10. Error Analysis

Produce a reproducible error-analysis artifact for the primary model M2.

At minimum identify:

- high-priority false positives
- missed positive cases / false negatives
- cases near the operational Top-K boundary
- examples where trajectory changes the ranking relative to a simpler snapshot baseline
- cases with short or sparse history if such cases exist
- any meaningful subgroup/slice already supported by the repository

For each selected representative child, retain enough non-sensitive synthetic evidence to inspect:

- child identifier
- relevant history
- latest HAZ
- outcome label
- predicted score
- rank
- key features
- explanation if available

Do not manually hand-pick only flattering examples. Define deterministic selection rules.

---

# 11. SHAP Evidence

Validate that the current SHAP implementation remains consistent with the actual persisted primary model.

For a small deterministic set of representative synthetic cases, export explanation evidence suitable for later use in the application/demo.

Verify:

- displayed SHAP values correspond to the same values used to infer direction;
- feature names map correctly to model inputs;
- explanation values correspond to the persisted primary model;
- explanations are described as **feature attribution**, not causal effects.

Do not change SHAP semantics merely for prettier output.

---

# 12. Model Persistence

Verify end-to-end model persistence:

1. train the primary model;
2. save it;
3. load it in a fresh process/session;
4. run inference on a fixed fixture;
5. verify predictions are numerically consistent within a strict justified tolerance.

Persist all metadata required for inference, such as:

- feature ordering/schema
- model version
- training configuration
- seeds
- relevant target metadata

Do not rely on implicit Python object state that cannot be reconstructed.

---

# 13. Reproducible Artifacts

Follow existing repository conventions where possible.

Produce machine-readable artifacts for:

1. per-seed metrics
2. aggregate metrics
3. baseline/model comparison
4. ablation results
5. grouped evaluation
6. temporal evaluation
7. capacity metrics
8. error-analysis cases
9. representative SHAP cases
10. final primary model metadata

Prefer CSV/JSON for raw results and Markdown only as a human-readable summary.

Do not commit huge generated files if the repository convention excludes them. If an artifact should not be committed, provide a deterministic generation command instead.

---

# 14. Final Summary Artifact

Create a concise technical summary in the repository, following existing documentation conventions, containing:

## Environment
- Python version
- important package versions
- Git commit

## WHO validation
- official source
- validation cases
- result

## Dataset
- generator configuration
- number of children
- number of visits
- seed list
- target prevalence per seed if relevant

## Evaluation
A compact comparison table for B0/B1/B2/M1/M2/M3.

## Primary model
Explicitly state that M2 was pre-specified as primary.

## Robustness
Report mean ± std across seeds.

## Ablation
Report feature-family contribution.

## Error analysis
Summarize important failure patterns.

## Limitations
Explicitly state that synthetic-cohort performance is:
- validation of pipeline/mechanism behavior,
- **not external clinical validation**,
- **not evidence that Tunas improves real-world child health outcomes**.

Do not write competition marketing copy. Keep this document technical and evidence-based.

---

# 15. Testing Requirements

Use systematic verification.

After each logical change:

1. run the smallest relevant test set;
2. inspect failures rather than patching around them;
3. add regression tests for any discovered bug.

Before completion:

- run the complete test suite;
- run the canonical final experiment command from a clean state;
- verify expected artifacts are produced;
- verify model reload/inference;
- inspect Git diff for accidental unrelated changes.

Do not disable tests.

Do not use `--no-verify`.

Do not reduce test coverage to obtain green results.

Do not suppress warnings without understanding them.

---

# 16. Change Discipline

Avoid broad refactors unrelated to this task.

Prefer minimal, clear changes.

Do not:

- modify frontend code;
- modify backend/API code unless a shared tabular library absolutely requires a compatibility correction;
- work on the paper;
- work on CV;
- upload anything to Hugging Face;
- change the product scope;
- redefine the prediction problem;
- tune against the final test split;
- delete existing historical results without preserving provenance;
- perform destructive Git operations;
- force-push;
- commit secrets;
- invent empirical results.

If temporary scripts/files are created during investigation, remove them before completion unless they are useful reproducibility tools.

---

# 17. Handling Uncertainty

Do not stop for minor ambiguities that can be resolved safely by inspecting the repository.

When repository code, tests, and documentation disagree:

1. inspect Git history if useful;
2. determine which behavior is actually exercised by tests/current pipeline;
3. preserve the scientifically safest interpretation;
4. document the discrepancy.

If a decision would materially change the research question, target definition, evaluation semantics, or previously frozen scientific design, **do not make that decision silently**.

Instead:
- preserve current behavior where possible;
- record the issue prominently in the final report.

Continue all independent work that is still possible.

---

# 18. Success Criteria

This task is successful only if, at the end:

### WHO
- Official WHO reference data have traceable provenance.
- Independent official validation passes.
- No WHO validation test remains skipped merely because required repository data are missing.

### Tests
- The full repository test suite passes, except skips that are genuinely optional and explicitly justified.
- New regression tests cover any bug fixed during this task.

### Final experiments
- B0/B1/B2/M1/M2/M3 are evaluated reproducibly.
- M2 remains primary.
- Grouped and temporal results exist.
- Capacity metrics exist.
- 3–5 seeds are evaluated.
- Mean ± std summaries exist.
- Ablation evidence exists.
- Error analysis exists.
- SHAP representative evidence exists.
- Persisted-model reload is verified.

### Reproducibility
- One documented command or small sequence of commands can regenerate the final tabular evidence from the repository and required official artifacts.

### Scientific integrity
- No claim extends beyond what synthetic data and the tests demonstrate.

---

# 19. Final Response Format

When the implementation is complete, respond with exactly these sections:

## 1. Baseline state
- Git HEAD
- initial test result
- skipped/failed tests and root causes

## 2. Changes made
For each changed file:
- path
- purpose
- important behavior change

## 3. WHO validation
- official source used
- provenance
- independent checks
- final WHO test result

## 4. Final experiment protocol
- dataset configuration
- seeds
- models
- splits
- metrics
- primary model

## 5. Final results
Provide concise tables containing the actual measured results.

Do not fabricate unavailable metrics.

## 6. Error analysis and SHAP
- key failure patterns
- representative cases created
- artifact paths

## 7. Reproducibility
Provide the exact commands needed to reproduce:
- tests
- dataset generation
- final experiments
- model loading/inference

## 8. Verification
- final full test result
- canonical experiment smoke test
- model persistence check

## 9. Files changed
List all modified/added files.

## 10. Remaining blockers
Only genuine unresolved blockers.

If there are none, write:
`None.`

---

# 20. Execution Instruction

Do not merely propose changes or write a plan.

Inspect the repository, execute the work, run the tests and experiments, inspect their outputs, fix issues you encounter, and leave the repository in the completed verified state described above.

Begin by inspecting the repository and establishing the baseline.

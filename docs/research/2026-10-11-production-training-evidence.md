# Production training admission from pre race source evidence

The current 2025 inputs are not approved for production training. Their compatibility manifests and missing per-race acquisition evidence do not establish that all model inputs existed at the prediction deadline. This is **unknown historical eligibility**, not confirmed leakage. No real model was fitted or promoted in this increment, and no new accuracy was measured. The target remains 70% exact race-level success for one unordered three-horse submission over the complete frozen race universe.

## Actual retained input audit

A read-only audit on October 11 found 1,758 races in each of `full_year_2025` and `full_year_2025_prerace_canonical_v2`. Both have zero `snapshot_meta` objects and legacy bootstrap markers in their manifest audit and candidate audit. These are two representations of the same historical research input, not 3,516 independent races.

The canonical dataset is 60,236,041 bytes with SHA-256 `7870b169992e0b108c75384733ef15e6c790fe62e1005433d007c80b84be9131`. Its answer key is 80,076 bytes with SHA-256 `1c9106b3fc338d1ba3cc2a283950f14747e812b892a572ed59f3a090d9fa03e0`. Its manifest is 293,908 bytes with SHA-256 `52ea1357fe222d4d7c99fa016ac842fab2827bcfbc0e1cd870c99c94178ac2a7`. Hashes identify the audited bytes; they do not prove pre-race availability or a complete national evaluation universe.

The actual trainer, invoked with the owner's retained configuration and snapshot directory, rejects it with `legacy bootstrap inputs are not eligible for production training`. No output parent was created. SHA-256 remained unchanged for the configuration, dataset, answer key, manifest, and existing champion. The champion hash remains `bde9fdfaee00c898ef468789e93219c039deb268a4144b98657998fa7b6b604d`. This is a real negative admission check, not an accuracy evaluation or an approval of that model.

## Reproduced admission defects

Before this change, an actual trainer invocation with synthetic legacy artifacts reached model creation, and an output parent was created before input validation. A separate configuration-change test showed that the parameter context recorded a hash of the original configuration while resolving C=2.0 from a later read rather than the original C=0.75. Both tests failed before implementation and now pass.

The old offline timing audit also passes five independent synthetic mutations: an unbounded/missing cutoff, unknown timestamp source and confidence, schedule-derived timing without an actual ready timestamp, an explicitly excluded race, and a timezone-free entry/ready timestamp. An older source revision with acquisition/ready after cutoff passes the old audit too. These are synthetic admission counterexamples, not evidence that a specific real model has leaked.

## Production boundary

`autoresearch/training_evidence.py` retains configuration, dataset, answer key, and manifest bytes once and parses those same bytes for both validation and fitting. The old offline resolver remains available for historical diagnostics; production never calls it and never synthesizes a missing compatibility manifest.

The minimum timing gate requires exact boolean eligibility/source flags, strict replay status, known revision/capture provenance, bounded timezone-aware start/cutoff/entry/ready times, and explicit capture completion. It requires entry <= capture completion <= ready <= cutoff < start. The capture-completion field is `snapshot_meta.source_lookup.capture_completed_at`; it must be corroborated against raw receipt evidence during review, not filled from a schedule, filesystem modification time, current database value, or old publication date. Full runner fields, identities, unique horse IDs, exact three-horse targets, dataset/manifest equality, and complete feature-row membership are also required. One ineligible race rejects the entire input instead of creating a passing subset.

Passing these conditions alone does not approve training. Production requires one unique exact recipe in the repository-controlled `data/contracts/production_training_reviews_v1.json`. There is no CLI registry override or legacy bypass. The initial approval list is empty. An approval pins SHA-256 and byte size for configuration, dataset, answer key, manifest, and the implementation fingerprint. It also references a content-pinned source-review document inside `docs/research`. The fingerprint covers the trainer, feature transformations and validation dependencies, field/timing CSV contracts, uv.lock, Python version, and relevant installed package versions. Drift before fitting or publication rejects the run.

This is a trusted repository review boundary, not an automated raw-source certification system. Adding a registry entry is a consequential evidence decision that requires review of the sources themselves. A self-signed dataset flag or a correctly shaped timestamp cannot substitute for that review. Tests inject an explicitly synthetic review root only to exercise the trust boundary; no synthetic approval is written into the canonical registry.

The trainer defaults to a new `candidate_clean.joblib`, refuses existing files and symlinks, and atomically publishes a complete candidate without replacing a model. Its compatible v1 bundle carries an additive training receipt with exact input/implementation/review pins, `model_promoted=false`, and `target_accuracy_verified=false`. No training admission automatically proves valid live inputs, unique pre-cutoff predictions, evaluation completeness, or 70% success.

## Source review requirements

Before approving any real recipe, establish an immutable raw inventory with identities, raw hashes, acquisition completion, publication/effective revision evidence, timezone and clock basis, pagination/full-field checks, and successful identity joins. Every selected feature must trace to the actual raw fields and transformation version. A mutable career statistic or same-day update needs its stored as-of version; an old event date in a current response is not sufficient. Required-source presence flags must be verified against the raw blocks. Review missing and conflicting records explicitly rather than reconstructing a convenient timestamp.

Acquisition after cutoff is not operationally available at cutoff, even when a provider reports an earlier revision. Preserve it as retrospective material. Any separate historical reconstruction must document independent evidence of the exact earlier source version and remain a diagnostic reconstruction until it satisfies an explicitly reviewed admissibility rule. Do not relabel the later acquisition as a pre-cutoff capture or use it as a forward prediction receipt.

The reviewed race membership must stay distinct from the full frozen evaluation universe. Training admission does not establish that all official national races are represented. Empty API pages, capture coverage, complete features for a subset, and the current saved model are not evidence of that universe or of goal success.

## Verification and remaining work

Local validation passed 358 tests without skips: 41 training-evidence cases, 98 existing scripts/prepare/train compatibility cases, and 219 source/PDF regressions. Ruff lint, formatting, and diff checks pass. Exact-head remote checks remain to be recorded before normal merge. Tests include a real scikit-learn fit and atomic joblib round trip on four synthetic rows; this is a software-path test only. Five local NumPy/joblib deprecation warnings are recorded, not suppressed as proof of a clean dependency audit. Current real approved recipes: zero. Current goal-qualified success rate: not established.

The next research work is a complete future race universe, a runnable fixed B0 with trustworthy single-submission receipts, and a feature-by-feature historical source review. Historical reconstruction can guide experiments but must not be substituted for the forward goal evidence. Freeze features and trial budgets before inspecting evaluation outcomes, and use the same full race denominator for comparisons. Do not create more validation infrastructure merely to repeat this finding; source evidence and actual frozen predictions are the next bottleneck.

The owner-authorized Pro follow-up was sent with these findings and is still generating. Its completed advice will be recorded only after completion; no response was stopped, and no private conversation URL or authentication material belongs in this public record.

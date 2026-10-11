# Require reviewed pre race evidence before production training

This ExecPlan is a living document maintained under `.agent/PLANS.md`. Keep Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective current.

## Purpose / Big Picture

The research target remains 70% exact race-level success for one unordered three-horse prediction per race over the complete frozen universe, using only pre-race inputs. This increment prevents the production trainer from interpreting a legacy offline compatibility manifest as evidence that historical inputs were available before a race. Running the existing training configuration must fail before fitting, creating an output directory, or replacing a model. Existing offline diagnostic evaluation remains available and unqualified.

A point-in-time input is the exact source version actually available at the prediction deadline, not a current value carrying an older event date. Structural timestamp checks are necessary but cannot prove source history. Production admission must also require a checked-in review of exact input bytes and feature source evidence. Initially there are no approved recipes because no reviewed historical source lineage has been established. Do not add a synthetic approval to the real registry or call a unit-test fixture evidence about actual races.

## Progress

- [x] (2026-10-11 08:54Z) Revalidated the active Goal and clean origin/main worktree without editing the owner's dirty checkout.
- [x] (2026-10-11 08:56Z) Reproduced five synthetic timestamp cases that pass the old offline timing audit but cannot establish training eligibility.
- [x] (2026-10-11 09:00Z) Sent a consolidated evidence question to the owner's authenticated ChatGPT Pro model through the authorized browser. Its completed answer is still pending; no new consultation result is claimed.
- [x] (2026-10-11 09:03Z) Rechecked both retained 2025 datasets: each has 1,758 races, zero per-race snapshot_meta objects, and legacy bootstrap markers.
- [x] (2026-10-11 09:05Z) Added two actual trainer/configuration regressions; both failed before implementation, showing legacy admission reached model creation and configuration parsing differed from the hashed read.
- [x] (2026-10-11 09:10Z) Implemented timing/full-field checks, the empty reviewed-recipe registry, single-read input buffers, implementation/environment pins, and atomic no-replacement candidate publication.
- [x] (2026-10-11 09:11Z) Passed 138 local training/compatibility tests and the actual owner's negative admission check; configuration, dataset, labels, manifest, and champion hashes are unchanged and no output directory was created.
- [x] (2026-10-11 09:14Z) Passed 358 combined tests: 41 training-evidence cases, 98 existing diagnostic/script cases, and 219 source/PDF cases. Ruff lint, formatting, and diff checks passed with no test skips.
- [x] (2026-10-11 09:15Z) Committed/pushed 86cdf92 and opened/attached draft PR #65; no owner-checkout files were staged or changed.
- [x] (2026-10-11 09:17Z) Read the completed Pro answer (UI processing duration 12 minutes 35 seconds), including its limited public-base review and source-positive admission caveat.
- [x] (2026-10-11 09:20Z) Verified first-head required Python/41 focused cases, Scripts, Docker, and Gitleaks passes. Dependency audit fails on the same 17 records in three packages as base main; later security stages are skipped.
- [x] (2026-10-11 09:37Z) Integrated actual fit-array/weight/order/cohort digests, normalization failure checks, external model-hash completion receipt, and owned-output rollback. Passed 375 combined regressions, including 58 focused cases, without skips.
- [ ] Push the Pro follow-up and verify exact final-head remote CI, then normally merge PR #65 without bypassing protection.

## Surprises & Discoveries

`audit_snapshot_manifest_races` passes each of five one-field mutations of a normal synthetic row: unbounded/missing cutoff, unknown timestamp source, schedule-derived timestamp without actual ready time, include_in_strict_dataset=false, and a timezone-free timestamp. This does not demonstrate actual training leakage. It demonstrates that this audit alone cannot authorize production training.

`train_clean.py` creates its output parent before validation, calls the legacy-permitting offline resolver, then rereads dataset and answers in its loader. `load_evaluation_parameter_context` also reads configuration once for its checksum and again for its parsed settings. A checksum of one read does not identify another read when a file changes between them. Validation and fitting must consume the same retained bytes.

The clean worktree contains the canonical 2025 manifest but not its ignored canonical dataset. The owner's retained artifact was inspected read-only, not copied or modified. Both retained 2025 datasets have no per-race timing metadata. Report missing evidence as unknown, not confirmed leakage or demonstrated model failure.

## Decision Log

- Decision: Preserve the old offline diagnostic resolver and add a production-specific admission boundary.
  Rationale: Compatibility with old research is useful but is not permission to train or promote an operational model.
  Date/Author: 2026-10-11 / Codex.
- Decision: Require a reviewed, checked-in recipe pinned to exact artifacts, in addition to structural timing checks; initially approve nothing.
  Rationale: Self-reported timestamps and flags cannot establish raw source or feature lineage. Automated admission must not silently certify them. Review must establish raw acquisition and publication versions, all feature dependencies, joins, full fields, and coverage before adding a real approval.
  Date/Author: 2026-10-11 / Codex.
- Decision: Keep the Pro generation running to completion while independent regression work proceeds.
  Rationale: The owner explicitly requires completed Pro advice without stopping generation or imposing a short response timeout. Do not publish the private conversation URL.
  Date/Author: 2026-10-11 / Codex.

## Outcomes & Retrospective

Implementation and local software-path acceptance are complete; remote acceptance is pending. No real-race model has been fitted, promoted, or scored, and the 70% Goal remains active. This is a narrowly scoped training admission increment, not a new evaluation universe or an accuracy improvement.

The implementation and local negative/positive software-path acceptance are now present. The positive fit is explicitly synthetic under an injected test review root, not a real pre-race-safe dataset. The owner's real legacy recipe is rejected without modifying any of the five retained artifacts. Actual remote checks and completed Pro advice are still required before final merge.

The completed Pro advice is now integrated. Fit-input digests identify the exact arrays passed to fit; the declared and actual populations, normalization summaries, and external result-model hash are connected. Completion uses individually atomic no-replacement files and owned-output rollback, not a claimed two-file transaction. A crash-created orphan receipt is not successful publication. The first pushed head passed required checks; the final follow-up still requires exact-head CI and normal merge. Actual real-source positive admission remains unperformed, with zero approved real recipes.

## Context and Orientation

`packages/scripts/ml/train_clean.py` builds a saved scikit-learn model from the `clean_model_config.json` recipe. `packages/scripts/autoresearch/dataset_artifacts.py` owns separated dataset, answer-key, and manifest files for offline evaluation. Its legacy branch deliberately accepts artifacts without historical timing evidence. `packages/scripts/autoresearch/research_clean.py` constructs feature rows and arrays, normalizing duplicate races and horses for diagnostic runs. Production admission must reject malformed full fields before those helpers can silently remove entries. `packages/scripts/autoresearch/parameter_context.py` parses configuration into existing Pydantic parameter types. Use this existing model-resolution logic while ensuring it parses retained configuration bytes.

A frozen input means an immutable byte buffer read once, with SHA-256 and byte size computed from that same buffer, and parsed from that buffer for every downstream operation. A reviewed recipe means a repository-controlled approval referencing a source review and the exact configuration, dataset, answer key, and manifest hashes. A review is a human-readable evidence decision, not a magic passed flag. No runtime flag may enable legacy production training or substitute an arbitrary approval registry.

## Plan of Work

Add focused tests under `packages/scripts/autoresearch/tests/` for the actual production admission and trainer path. Add a cohesive training-specific input module alongside `dataset_artifacts.py`; reuse existing artifact hash records and temporal/field validators where appropriate without widening their offline behavior. Retain input bytes before parsing, validate all race identities and complete distinct runners/answers, reject legacy metadata and all five synthetic timing bypasses, and require the canonical reviewed-recipe registry before fitting. Unknown source lineage must remain rejected even when every timing field looks valid.

Update `parameter_context.py` to parse the bytes used for its own checksum, preserving existing callers. Route `train_clean.py` through the frozen training input rather than rereading offline paths. Validate before output creation and refuse replacing an existing output. Save a candidate with an additive training receipt, no automatic promotion, and no claim of leakage-free accuracy. Pin the retained configuration and data artifacts in the receipt. Do not change feature definitions, model parameters, historical observations, or the owner's model.

Use the existing API CI environment for an explicit focused training test step because it already has NumPy, joblib, and scikit-learn. Do not add large dependencies or update the lockfile only to make this test run. Keep existing required jobs and security checks intact. Integrate the completed Pro answer before finalizing admission policy and publication.

## Milestones

The first milestone records failing regression tests showing that the current trainer can proceed on a synthetic legacy input and create output state before refusing invalid input. The next milestone makes those cases fail closed before fitting and validates the byte-freeze behavior, while legacy offline diagnostic loading still works. The final milestone exercises the current owner's configuration without writing anything, proves zero approved real recipes, records the completed Pro advice and remaining research priorities, and publishes through normal checked CI and merge.

## Concrete Steps

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf` on `codex/strict-prerace-training-evidence`, starting from origin/main `1c65fccc6e913daa724f41ccd9889c364fad32dd`. The original checkout has unrelated owner changes and must not be staged, reset, or committed. Use apply_patch for manual edits and reviewed escalation for writes/tests/Git. Tests use only disposable temporary artifacts and stub fit calls where testing rejection; any positive training-path fixture is explicitly synthetic and is not a real source approval.

From the worktree root, run the focused test with the existing dependency environment:

    .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_training_evidence.py

Run Ruff lint with --no-cache and format checks on changed Python files, `git diff --check`, and existing source regressions. Inspect the actual CI invocation and exact-head result. A skipped job or test is not a pass. Never suppress a failure, force a merge, or change branch protection. Attach every created PR to this chat.

## Validation and Acceptance

The actual trainer must reject the old legacy recipe without calling fit, creating a model/output directory, changing artifact files, or overwriting a pre-existing model. The production loader must not bootstrap a missing manifest. It must reject naive or unbounded time, unknown/schedule-only timestamp provenance, excluded or non-strict races, late captures despite an older source revision, absent source reviews, inconsistent identities, missing/duplicate runners, malformed targets, and partial dataset membership. One ineligible race rejects the entire input, never yields a passing subset.

Tests must prove that changing an artifact or configuration on disk after freezing cannot change the parsed input or checksum consumed by training. A self-signed passed flag must not satisfy review. The real approval registry remains empty until an evidence-backed source review is actually completed. Positive acceptance tests exercise an injected synthetic reviewed recipe only; describe that trust-boundary fixture explicitly. The existing legacy offline resolver still supports unqualified diagnostics.

## Idempotence and Recovery

No old model or snapshot is rewritten. Tests may be rerun in their own temporary directories. Rejection has no output side effects. The trainer refuses an existing output, including a symlink, instead of clobbering it. If a write fails, remove only a newly created temporary candidate owned by this invocation and leave any existing output intact. Preserve failed source evidence and the branch when checks fail. The change can be reverted with a normal reviewed commit without resetting owner work.

## Artifacts and Notes

Canonical owner dataset SHA-256 is `7870b169992e0b108c75384733ef15e6c790fe62e1005433d007c80b84be9131`, 60,236,041 bytes. Its manifest SHA-256 is `52ea1357fe222d4d7c99fa016ac842fab2827bcfbc0e1cd870c99c94178ac2a7`, 293,908 bytes. Its answer key SHA-256 is `1c9106b3fc338d1ba3cc2a283950f14747e812b892a572ed59f3a090d9fa03e0`, 80,076 bytes. These identify the read-only audit input, not an approved training set or source availability proof.

## Interfaces and Dependencies

Use standard-library bytes, JSON, datetime, SHA-256, pathlib, and the existing Pydantic/scikit-learn/joblib/pytest environment. Avoid adding a new framework. The training input object must expose retained configuration/data/labels/manifest through byte-backed parsing and exact hash records. The production trainer calls this admission once and uses the returned buffers, never the offline resolver. The registry is repository-controlled and has no CLI bypass. Keep bundle schema compatibility through additive receipt fields, and record model_promoted=false.

Revision note (2026-10-11 09:04Z): Created before implementation from reproduced timing-admission failures and a read-only inventory. Pro advice remains pending and will be integrated only after its response completes.

Revision note (2026-10-11 09:12Z): Recorded reproduced failures, byte-frozen admission and implementation/environment bounds, local tests, and the actual owner-artifact negative check. Added a synthetic fit only as a software-path test. Remote checks and completed Pro consultation remain incomplete.

Revision note (2026-10-11 09:14Z): Recorded 358 passing combined regressions, including both parameter-context readers. The five dependency deprecation warnings in the synthetic joblib read are not failures or accuracy evidence. Remote publication and completed Pro advice remain pending.

Revision note (2026-10-11 09:37Z): Integrated the completed Pro advice before final publication. Added fit-population and consumed-matrix linkage, completion model hash, failure preservation, and actual entrypoint negatives. Updated local acceptance to 375 cases, separated synthetic path validation from unperformed real-source admission, and documented the two-file crash limitation. Final exact-head checks and normal merge remain pending.

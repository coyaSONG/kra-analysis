# Bind semantic interpretations to actual review evidence

This living ExecPlan follows `.agent/PLANS.md`. It builds on the observation
reader from PR122 without activating any future study, choosing dates or N,
fitting models, or changing any original predictions.

## Purpose / Big Picture


A public document with `reviewer: name` does not prove that account reviewed
those bytes. The next source-evidence component must distinguish a mechanically
replayed schedule row from an authorized person's interpretation of an official
notice. A read-only auditor will verify exact original source bytes, a narrowly
typed claim, an owner-authorized reviewer registry, the actual GitHub review,
and the reviewed commit's exact document bytes. Its output is an attested
interpretation, not machine verification of the source's meaning or population
closure. This makes an essential future evidence path usable without pretending
an approval boolean closes an unknown scope.

## Progress


- [x] (2026-10-20) Inspected clean isolated checkout at PR122 merge `1d0ab4b`.
  Previous goal turn made progress: PR122 was implemented, tested and merged.
- [x] (2026-10-20) Read the completed Pro design consultation record and current
  publication/source helpers. Consulted official GitHub reviews/contents API
  documentation and read public repository owner ID `66289470`.
- [x] (2026-10-20) Implemented strict archived review/commit-content evidence.
- [x] (2026-10-20) Implemented narrow semantic claim/source/authority audit.
- [x] (2026-10-20) Added 55 synthetic cases and required Python CI coverage.
- [x] (2026-10-20) Local related regressions: 427 passed in 38.50s; Ruff check
  passed; six frozen artifact SHA256 values unchanged.
- [ ] Commit, push, verify remote required checks and normally merge.
- [x] Leave source completeness, identity projection, submission/target admission
  and actual registration as explicit remaining gates.

## Surprises & Discoveries


PR120's low-level archive helper verifies document publication; its approval
record checks a reviewer name and flags, not a GitHub review by that account.
The new path must reuse only the public-byte helper, not pretend a notice is
a weekly protocol. GitHub reviews expose `user.id`, `state`, `submitted_at`
and `commit_id`. Contents can be read at that exact commit. A later document
version cannot reuse an old approval just because the path is unchanged.

The existing strict JSON helper accepts only objects, while the GitHub reviews
endpoint returns an array. The first end-to-end test exposed this mismatch.
The new response reader uses the standard JSON parser with the existing
duplicate-key/nonfinite-number rejection hooks, leaving shared historical
parsers unchanged. Added tests cover both rejection hooks and an object where
an array is required. Empty scope claims also validate physical dates/venues.

## Decision Log


Decision: use a separately published authority registry authorized by an
actual APPROVED review from repository owner ID 66289470, with a review body
binding exact registry and policy hashes. Registry author and approving account
must differ. Rationale: neither a caller-selected registry nor owner merge alone
is a grant of reviewer authority. The owner's public ID was read from the
repository API; no real registry or grant is created here. Date/Author:
2026-10-20 / Codex.

Decision: require the decision reviewer to be delegated for its claim type
at the time of review, different from the PR author, with an exact structured
review-body commitment and matching content at the reviewed commit. Preserve
the review-list snapshot after publication; reject dismissed/outdated opinions,
unresolved changes requests and incomplete pagination. Rationale: review text
or a user name alone cannot bind actual reviewed bytes. Date/Author:
2026-10-20 / Codex.

Decision: the initial bounded archive format accepts one complete review page
of fewer than 100 entries, queried explicitly with per_page=100/page=1; a full
page is unsupported, not silently complete. Rationale: no current need for a
general pagination collector; no live requests are made by replay.
Date/Author: 2026-10-20 / Codex.

Decision: only preserved official KRA HTML/text notices with a literal excerpt
and exact URL/receipt/body hashes are supported initially. Source meaning
remains human interpretation. No automatic natural-language implication,
population closure, training authorization or scoring result is produced.
Date/Author: 2026-10-20 / Codex.

## Outcomes & Retrospective


Implementation and local tests are complete; remote CI/merge are pending.
The 70% objective is not achieved. This component
must not claim its accepted interpretation proves the entire population,
historical feature availability or unique target existence. Actual source
notices and owner/reviewer evidence still require a separate collection and
human authorization workflow.

## Context and Orientation


Use `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`, branch
`codex/semantic-review-evidence`. Leave the dirty original user checkout alone.
`condition_historical_publication.archive` validates four pinned original
GitHub archive files. `condition_population_ledger` currently preserves all
semantic events as unverified assertions; do not change its meaning in this
milestone. `condition_outcome_accounting` consumes normalized states and must
not be called here.

An authority registry is a versioned list of account IDs, claim types and
validity periods that the owner has actually reviewed. A semantic decision
is a bounded interpretation of identified source documents. Its claim is not
automatically true because its authorship/provenance is verified.

## Plan of Work


First add a narrow review archive validator. Each SHA-pinned archive manifest
identifies repository, PR, selected review, observation time, the complete
review-list response and the contents response at the selected review commit.
Validate canonical request URLs, status, observation clocks, exact account
IDs, APPROVED state, author separation, same document/path/hash at reviewed
commit and merge, and structured body commitments. No latest/current remote
lookup is permitted during replay.

Then add the semantic auditor with fixed code-defined policy. Its root
manifest binds umbrella hash, as-of time, registry/decision publication
archives, each review archive and source captures. Validate registry owner
approval, delegated claim scope, source-before-review chronology and exact
claim fields. A small explicit claim set includes no originally enrollable
races, same/different physical events, postponement, cancellation and exhaustive
scope listing. No general complete=true claim is accepted.

Finally prove behavior with generated synthetic public archives, API review
responses and official-source-shaped captures. The tests must show accepted
attestation with false machine-semantic/scoring flags, and rejection or pending
for forged names, changed reviewed bytes, wrong commit URLs, stale/dismissed
reviews, wrong claim authority, unknown fields, incomplete review pages,
noncanonical source URLs, missing originals, time conflicts and wrong excerpts.
No real authority or future interval is published by the tests.

## Concrete Steps


Use `.venv/bin/python -B`, `PYTHONPATH=packages/scripts`,
`PYTHONDONTWRITEBYTECODE=1` and pytest `-p no:cacheprovider`. Run Ruff without
cache on new modules/tests. Reuse existing helpers and dependencies only.
Add exact commands and results here during implementation. Add a dedicated
step to the required Python Checks job using existing uv/pytest patterns.

Executed in the isolated checkout:

    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_condition_semantic_review.py packages/scripts/autoresearch/tests/test_condition_population_chain.py packages/scripts/autoresearch/tests/test_condition_population_ledger.py packages/scripts/autoresearch/tests/test_condition_snapshot_replay.py packages/scripts/autoresearch/tests/test_condition_historical_publication.py packages/scripts/autoresearch/tests/test_condition_outcome_accounting.py packages/scripts/autoresearch/tests/test_condition_forward.py packages/scripts/autoresearch/tests/test_condition_training.py

    427 passed in 38.50s

Ruff check passed for the five new Python files. Formatting was applied by
Ruff. The tests use synthetic evidence only. Frozen A24/B34 model hashes,
training receipt, empty forward registry and M0/API27 commitment hashes all
match their original pinned values. No production training or inference ran.

## Validation and Acceptance


An end-to-end synthetic bundle must verify an actual owner review of registry
bytes, then a different delegated review of exact decision bytes, then a pinned
official-source excerpt. Output must distinguish attestation from machine
meaning, with scoring=false, N=null, fit_count=0 and no registration. Changing
only a declared reviewer name cannot make missing review evidence pass.
Input byte hashes must be unchanged after audit; trap network, subprocess and
live inference. Original six frozen artifact hashes must remain unchanged.

## Idempotence and Recovery


Replay is stdout-only. Missing evidence may be recovered by preserving exact
original bytes in a separate authorized workflow, not by fabricating reviews
or modifying old source captures. Source corrections require new versions.
No approving reviews, comments, grants or actual registry documents are created
as a side effect of implementing this auditor.

## Artifacts and Notes


Official API documentation:
`https://docs.github.com/en/rest/pulls/reviews` and
`https://docs.github.com/en/rest/repos/contents`.
The completed Pro consultation is linked and summarized in
`docs/research/2026-10-20-condition-population-observations.md`.
It is design advice, not an actual semantic approval or independent code test.

## Interfaces and Dependencies


Add `condition_review_evidence.py` for archived GitHub review binding,
`condition_semantic_review.py` for the stdout-only audit, and focused tests.
Keep publication, semantics, population projection and scoring separate.
Use existing strict JSON, timestamp, path and hash helpers. State the
cooperative-operator archived-HTTPS trust model explicitly; do not claim
defense against a party forging every archived response.

Revision (2026-10-20): recorded implementation, the array-parser correction,
55 adversarial cases and local regression results. The documentation explicitly
leaves correction admission unsupported and all real registration gates closed.

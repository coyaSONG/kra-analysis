# Official-notice interpretation review evidence

Status: read-only evidence component, not an actual authorization, future study
registration, population closure, inference run or training run. A24/B34 remain
frozen. Future dates, actual N and enrollment remain UNSET.

## What this verifies

`condition_semantic_review` replays preserved evidence that an authorized account
approved exact interpretation-document bytes. It does not decide whether the
human's interpretation follows from the official source. Accepted output is
`reviewer_attested_interpretation`, never a mechanically verified semantic fact.
The population observation reader still treats semantic events as unverified;
this component is not wired into admission or the outcome accounting reducer.

There are two separate public documents and reviews. The owner-authorized
registry is at `data/contracts/condition_semantic_authorities_v1.json`. The owner
anchor is repository account ID 66289470, login coyaSONG, read from the public
repository API. A separate author must submit the registry and the owner must
actually APPROVE its exact bytes. Registry publication must precede the decision.
A delegated account with the appropriate claim type and valid time interval
must then APPROVE the exact decision, separately from its PR author.

The policy and registry are hash-bound. Each review body is a JSON commitment
with `format_version=condition-semantic-review-commitment-v1`,
`document_sha256` and `policy_sha256`; decision reviews additionally bind
`authority_sha256` and `umbrella_sha256`. The helper `commitment` generates this
shape but never submits it. Public merge alone, a reviewer name, a boolean or a
comment is not an approval.

## Archived inputs

The root manifest uses `format_version=condition-semantic-review-v1` with
`as_of`, `umbrella_sha256`, `authority`, `authority_review`, `decision`,
`decision_review` and `sources`. Paths are root-relative, SHA256-pinned regular
files; symlinks, traversal and hash mismatches are rejected. `authority` and
`decision` use the existing four-file publication archive contract. The exact
canonical JSON bytes at merge must also match those at the reviewed commit.

Each review archive has `format_version=condition-review-archive-v1`,
`repository`, `pull_number`, `review_id`, `observed_at`, `reviews`,
`reviewed_content`. The last two fields contain `url`, HTTP `status` and a
`response` path/hash pin. Preserve the original GitHub review-list JSON and
contents JSON. Review-list URL must explicitly query `per_page=100&page=1`.
This bounded version only accepts fewer than 100 entries; a full page is
unsupported, not treated as complete. Contents must be requested at the
selected review's exact `commit_id`, not main or a later merge.

The selected review must be APPROVED and the account's latest actionable
opinion in the selected archived snapshot. Dismissed approvals, pending reviews,
later replacement opinions and unresolved changes requests block replay.
Observation must follow merge and precede the selected analysis as-of time;
as-of cannot be future. Review must precede merge. Each publication archive
must also have been retrieved by as-of. This proves the selected historical
snapshot only, not the current remote review state.

Decision documents use `format_version=condition-semantic-decision-v1` and the
path `docs/research/semantic-decisions/{decision_id}.json`. Required fields are
the ID, policy/authority/umbrella hashes, `authored_at`, `claim_type`, `scope`,
`subjects`, `claim`, `justification`, `sources`,
`supersedes_decision_sha256`. Scope contains sorted unique `race_dates` and
`meets`; subjects map immutable enrollment IDs to canonical date_meet_race IDs.
The explicit supported claims are:

| Claim | Subjects | Claim fields |
| --- | --- | --- |
| no_enrollable_races | zero | none |
| exhaustive_scope_listing | zero | race_ids (nonempty, sorted, unique) |
| same_physical_event | two | none |
| different_replacement_event | two | none |
| postponement | one | new_race_id, effective_at |
| cancellation | one | effective_at |

Each source selection binds `capture_sha256` and a literal `excerpt`. Its
receipt uses `format_version=condition-official-text-capture-v1`, `url`,
`status`, `fetch_started_at`, `capture_completed_at`, `content_type`, `encoding`
and `body` path/hash. Only HTTPS race.kra.co.kr/www.kra.co.kr text/html or
text/plain, HTTP 200, UTF-8/EUC-KR/CP949 are accepted. Maximum body size is 5MiB
and excerpt length 4096 characters. Source capture must finish by decision
authorship, which must precede delegated review. Effective time is separate
and can describe a future change. This format is not a notice collector.

## Run and interpret

From the repository root, with an independently collected evidence bundle:

    PYTHONPATH=packages/scripts PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \
      -m autoresearch.condition_semantic_review \
      --manifest /absolute/path/manifest.json --sha256 EXPECTED_MANIFEST_SHA256

Stdout is the only output. Exit 0 means attestation replayed, not that the claim
is true. Missing original files return `pending_evidence`; malformed, altered
or contradictory evidence returns `blocked` through the CLI (exit 2).
Every result leaves scoring false, actual fit count zero and denominator null.
No outcome files, live network calls, training or inference are needed.

Synthetic tests create all archives under temporary directories, including
fictional PRs/reviews and notices. Their dates are fixtures, not registration.
No real registry, owner grant, approval review, notice or decision is published
as part of this implementation.

## Trust and remaining gates

This is a cooperative-operator audit of preserved original GitHub/KRA HTTPS
responses, not a cryptographic defense against someone forging all archives.
Literal excerpt membership cannot establish implication, complete context,
attachment coverage, whether a notice concerns a race rather than an individual
entrant, or that no later notice was omitted. The reviewer must assess those
issues; a wrongly interpreted source may still pass the provenance checks.

The umbrella is hash-bound but its publication and membership are not validated
here (`umbrella_publication_verified=false`). Actual authority grants, scope
closure, identity projection, immutable submission attribution and target
admission remain separate work. This initial version rejects any non-null
`supersedes_decision_sha256`: corrections require the previous decision's full
evidence and a future versioned admission policy, not last-write-wins.
No selected interpretation sets N or justifies excluding an observation.

The original 70% full-universe objective is not achieved by this engineering
milestone. The completed Pro consultation summarized in
`2026-10-20-condition-population-observations.md` informed the design; it did
not review the new implementation or approve any actual decision.

Official evidence shape references:
[GitHub reviews API](https://docs.github.com/en/rest/pulls/reviews) and
[GitHub contents API](https://docs.github.com/en/rest/repos/contents).

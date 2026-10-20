# A24 and B34 historical publication audit

## Scope and current status

`autoresearch.condition_historical_publication` implements a read-only audit
of the original protocol, separately published approval registry and paired
prediction archives. It is the publication-provenance component proposed in
[the evidence review](2026-10-20-condition-evidence-boundaries.md), not the
complete historical inference or outcome evaluator.

The audit checks selected original bytes without calling current admission,
runtime, registry/Git lookups, fitting, inference, staging or live collectors.
It does not require the original local output copy to survive. It does require
the selected public archives to be preserved and pinned. An empty current
registry or a later local failure marker cannot override those public facts.

No real study manifest or execution protocol is created by this change.
The prospective registry remains empty, actual evaluation dates and N are
UNSET, and A24/B34 retain their original models and exhausted one-fit budgets.
The 70% research objective is not achieved by this component.

## Input and invocation

From the research checkout with `PYTHONPATH=packages/scripts`, run:

```sh
.venv/bin/python -B -m autoresearch.condition_historical_publication \
  --manifest /absolute/path/to/preserved/manifest.json \
  --sha256 THE_EXACT_64_HEX_MANIFEST_SHA256
```

This example is an invocation template, not a registered study. The command
prints JSON to stdout and writes no files. Its input is a new audit manifest,
not a replacement for the published protocol or approval registry.

The root manifest has exactly these fields:

| Field | Required value |
| --- | --- |
| `format_version` | `condition-historical-publication-v1` |
| `study_id` | The original registered study identifier |
| `protocol` | Exact protocol publication reference |
| `approval` | Exact separate approval-registry publication reference |
| `prediction` | Exact paired-prediction publication reference |

Each publication reference contains `pull_number`, repository-relative
`document`, exact document `sha256` and `files`. `files` maps the four existing
archive names `pull.json`, `document-response.json`, `observed.json` and
`published-document.md` to `{path, sha256}` pins. File paths are relative to
the manifest directory and may not contain traversal, empty components or
symlinks. Reads are bounded at 32 MiB per file. File pins are checked before
the byte-only publication verifier runs, without rereading those files.

Protocol documents must be under `docs/research/protocols/`. Approval must be
the original published `data/contracts/condition_forward_reviews_v1.json`;
the protocol and approval PR numbers must differ. The prediction document
must be `docs/research/commitments/condition-forward-v1/STUDY/paired.json`.
The approved registry entry must link the exact protocol path/hash/PR,
study, dates and required review flags, with a named reviewer.

Pinning a manifest is not approval, and review flags are recorded historical
assertions rather than independent proof of raw-source safety. The original
registry/approval process remains part of the trust model.

## What the audit establishes

The existing GitHub verifier checks repository, main-branch merge metadata,
exact merge-tree document URL, Git blob size/hash and decoded bytes. The
archive also binds raw response hashes, preserved document bytes and the
retrieval timestamp. Original canonical JSON must match the selected hash.
The audit assumes cooperative preservation of GitHub HTTPS observations;
it does not protect against fabrication of every local witness.

Cross-document checks link the published paired document to the original
protocol/runtime hashes, fixed model hashes and training receipt. It checks
declared race identity/order, exact race count, roster runner count, per-race
cutoffs and both arm keys. It checks each published selection's three distinct
positive horse IDs against the exact roster representation without silently
normalizing away leading zeros. A malformed B34 selection does not erase
A24's independent shape/membership result when the shared envelope is valid.

These are checks of public document consistency and selection shape, not
proof that scores or preprocessing were computed correctly. The audit does
not reconstruct the full protocol's source-derived invariants, official
schedule, feature matrix or numerical environment. Declared race count is
not a verified full-population denominator.

Recorded protocol/review/computation clocks must be consistent with the
original publication sequence. Both protocol and approval must be public by
the recorded computation time, and computation must precede prediction merge.
The original contract permits review before protocol merge, so no retrospective
restriction is added for that ordering. Every selected merge must be strictly
before the earliest block cutoff to receive a timely publication flag.
Retrieval after cutoff is allowed when it verifies an earlier server merge.
Output timing fields explicitly say `declared`: they compare against the
published protocol's cutoff, not an independently replayed official schedule
or a verified real-world pre-race availability boundary.

An arbitrary selected late PR is only a late-publication fact: it does not
establish that all accepted submissions failed. That requires the separately
specified closed submission slots and complete termination evidence.

## Result interpretation

| Status | Meaning |
| --- | --- |
| `public_chain_replayed` | All three selected archives were replayed and linked; inspect timing and arm shape results |
| `pending_evidence` | Selected archive files are missing; other verified public-byte facts remain visible |
| `blocked` | Invalid manifest, corrupt pins, malformed source evidence or structural/cross-document conflict |

Exit code 0 means the selected public chain was inspected, not that the
prediction or experiment is valid. A late chain or an arm with a malformed
selection can still be inspected successfully. Exit code 2 denotes pending
or blocked audit. The result always sets `usable_for_scoring=false`,
`counts_as_70_percent_evidence=false`, `actual_fit_count=0` and
`outcomes_loaded=false`. No `PredictionEvidence`, hit/miss count, accuracy or
denominator is produced.

Historical inference validity, raw-input provenance, submission closure and
umbrella population remain explicitly unverified. The report includes the
selected manifest hash, archive witnesses, original runtime/model/matrix pins
where available, actual audit time and hashes of the audit/publication/GitHub
validator modules. Those code hashes identify this verification stage, not a
complete preserved runtime. Missing files cannot create proven absence or
invalidity. Known conflicting evidence is not hidden by another missing
archive.

## Verification and remaining work

Synthetic tests exercise the CLI and evidence chain without fitting or actual
inference. Live admission/runtime/Git/network/fit/run/stage entry points are
trapped. Tests cover current-checkout independence, loss and corruption of
copies, each missing archive file, wrong authority and GitHub metadata,
cutoff equality, delayed witness retrieval, protocol/approval clocks,
race/roster/envelope conflicts, per-arm malformed selections, path escape,
symlinks, manifest flags and unchanged original bytes. Existing forward,
accounting, result observation and historical M0 regressions run alongside
them. Required Python CI includes the new suite.

Local result on 2026-10-20 UTC: 262 tests passed in 6.35 seconds, including
74 new cases and 188 existing regressions. Ruff lint/format passed. A24/B34
stored models and M0/API27 original prediction hashes matched the published
pins; the unchanged empty registry hash was
`891a83d52d409a109c24a0e2ef4c4ec695e57caf4fb8338911f49014a7603e30`.

Before scoring real prospective races, still implement and separately review
original code/environment/input replay, closed submission authority and
closure collection, append-only umbrella inventories and physical-race identity,
explicit no-target admission and the final evidence-to-accounting adapter.
The existing PR118 arithmetic and M0/API27 historical evaluator are unchanged.
This module supplies evidence for that path; it does not bypass any remaining
activation gate or select a future calendar.

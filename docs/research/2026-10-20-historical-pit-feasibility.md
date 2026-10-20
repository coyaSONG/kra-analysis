# Historical pre race input feasibility

## Fixed inspection scope

This source-feasibility inspection follows the completed Pro consultation
recorded in [PR132](https://github.com/coyaSONG/kra-analysis/pull/132).
It is not a model experiment, training permission or future registration.
The 70% exact single unordered triple objective is unchanged.

Before inspecting additional target contents, enumerate only paths named
`entry_capture.json` under the original and isolated research checkouts'
`.cache/autoresearch` directories. The read-only path inventory on 2026-10-20
found 4 original-checkout paths and 481 isolated-checkout paths. Repeated
requests are not distinct races or new training samples.

Conservatively exclude the already-investigated target dates October 10, 11,
16, 17 and 18, 2026. This excludes whole dates rather than claiming that every
possible race on them was used. It is an explicit investigation boundary,
not an evaluation-population filter. Derived legacy June datasets already
covered by the October 12 inventory are context, not newly discovered inputs.

The remaining request identities, derived from directory metadata only, are:
`20260705_1_1`, `20260824_4_1`, `20260825_4_1`, `20260831_4_1`,
`20260913_4_1`, `20260920_4_1`, `20261004_4_1`.

Select **20260705_1_1, 20260824_4_1 and 20260825_4_1**, sorted by date, numeric
venue and race number. Each has one matching manifest path. Do not replace
an unsuccessful example, inspect the other four for a better result, load
target outcomes or compute model scores. These are requested identities,
not yet verified official races, complete rosters or previously unseen data.

Positive control: the original October 10-11 PDF/API26 archive, using its
first identity `20261010_1_1` and already-preserved PR61 publication witness.
It is a known development source, never new data or an independent holdout.

Inspect three source paths only: existing archives, the official race-card
publication board identified by the saved source metadata, and official API26
documentation for version/as-of support. No authenticated API queries, bulk
historical downloads, replacement targets or changes to stored models are
authorized by this inspection. A missing version guarantee is not evidence
that no other archive exists. Dates, future N and execution registry stay unset.

## Result

The selection above was committed as `66eb723` before the three additional
manifests were opened. The bounded inspection found **zero new usable pre-race
packets among those three requests**. This is not an estimate of availability
in other archives and does not establish that the requested races existed.

| Requested identity | Preserved observation | Classification and consequence |
| --- | --- | --- |
| 20260705_1_1 | October 12 request; `invalid_entry_response`; no retained response page or completion time | Unknown response. Cannot reconstruct authentication, rate-limit or unpublished status; no roster |
| 20260824_4_1 | October 11 completion at 13:36:12.780454 UTC; one 135-byte page, API code 00, zero rows | Successful empty response, availability unconfirmed; no roster |
| 20260825_4_1 | October 11 completion at 13:36:17.684085 UTC; one 135-byte page, API code 00, zero rows | Successful empty response, availability unconfirmed; no roster |

The August page hashes match each other because their empty response bytes
are identical, not because their requested identities or races are identical.
Their shared SHA256 is
`6792ad188c3100a16278a4b648efe050c0dbc8190f322815df8d22de59bb03d8`.
Both page lengths, hashes, pagination and request identities were checked.
Neither empty response proves no race, nor what was available before August.
The July manifest lacks enough response evidence for a more specific diagnosis;
do not retroactively fill it using the later PR132 diagnostic fields.

Exact manifest pins and local paths are in the offline
[inspection companion](historical_pit_feasibility_check.py). It reads only the
three selected manifests and the known positive-control chain, makes no network
requests, and emits aggregate JSON to stdout. It is a fixed research check,
not a generalized admission tool or permission to train.

## Positive control

Replayed only `20261010_1_1`, using the existing PDF/API26 raw-source validator.
Raw PDF and entry-page hashes, identity joins and **11 feature rows** matched
the published feature projection. The preserved PR61 metadata verifies a merge
at **2026-10-09T17:08:16Z**, before the control's October 10 cutoff; local source
completion, plan pinning and bundle export also precede that merge.

The published input-plan and feature-bundle pins remain respectively
`0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0` and
`8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6`.
The archived public document SHA256 is
`f82dacb7132d871af231fa147152bef96445d16a5223e6cc4e9f7abfcdafeda7`.
This check replays saved GitHub responses and their Git blob identity; it is
not a fresh HTTPS publication witness. It relies on the preserved witness's
provenance and hash-preimage resistance. Current parser agreement does not
claim an identical original runtime. The control is already-used development
evidence, not a new training sample or independent validation.

## Official historical publication path

On October 20, 2026 around 19:56 UTC, a single focused board title search for
the selected July 5 date found the
[official Seoul post 247930](https://board.kra.co.kr/board/viewPost.do?boardNo=68&artNo=247930).
It displays registration time **2026-07-01 18:00:03** without an explicit timezone
in the inspected text. It lists PDF attachment `s_run_hr_260705_all.pdf` with
file ID 153392 and a July 5 ZIP with file ID 153393, among other attachments.
This is useful evidence of a dated publication record, not verification of
the requested race-1 roster or immutable pre-race attachment bytes.

The inspected post exposes no historical content digest, revision chain or
attestation that today's attachment is the original edition. No attachments
were downloaded, no roster was reconstructed, and no source was admitted.
The browser observation above is recorded with its URL and observation time;
it is not a preserved raw-response snapshot and has no claimed raw hash.

The [official API26 introduction](https://www.data.go.kr/data/15058677/openapi.do),
inspected in the same bounded investigation, describes a real-time entry
service and a recent-month default when dates are omitted. The inspected
introductory page does not establish an immutable historical version or
as-of retrieval guarantee. That is a documentation gap, not proof that such
archives cannot exist. No authenticated API query or documentation-attachment
inspection was performed. Historical query dates alone cannot prove that
returned fields match what was available before the target cutoff.

## Decision and validation

Do not substitute later results, current horse attributes or a dated board
title for missing historical target inputs. A useful next historical source
would need an exact original edition, full roster and feature provenance,
plus evidence binding those bytes before the original cutoff. Any wider
search needs a separately bounded scope, not replacements for failed examples.
Keep collecting complete future blocks only when actual official schedules
and the existing admission gates permit it. Do not tune the existing small
sample again or enlarge it with unverifiable historical packets.

The A24/B34 [preregistration draft](2026-10-20-condition-preregistration-draft.md)
remains a draft: exact dates, N and population are unset; no execution registry
entry, inference or training was created. Existing commitments and fit receipts
are unchanged. The 70% goal remains unmet. PR132's separately recorded security
hold is not resolved by this source investigation.

Reproduce the offline check from the research checkout with its existing venv:

```sh
PYTHONPATH=packages/scripts PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  docs/research/historical_pit_feasibility_check.py \
  --research-root "$PWD" --original-root ../kra-analysis
```

The check passed: three request manifests, two empty response pages, one
positive-control raw chain and 11 published feature rows. Target outcomes,
stored-model scoring and fit functions are not called.

The [source-readiness registry snapshot](source-readiness-2026-10-20.json)
records these three failed requests, the board lead, the known control and
the most recent existing schedule capture as six scoped observations. It is
not an exhaustive catalog or machine admission policy. Each row separates
collection/availability, joins, scoped coverage, missingness and leakage risk.
Null missing rates mean no known denominator, not zero missingness. Confirmed
control joins do not establish nonmissing feature values or future coverage.
The offline companion checks registry facts against the selected raw evidence,
including all four schedule raw hashes. The browser-only board note remains
explicitly outside raw replay. Collection completion and later review clocks
are separate. No new schedule/API request is made by registry validation.

Regression validation: `test_prerace_hash_witness.py` and
`test_kra_race_card_pdf_replay.py` passed **115 tests in 7.90 seconds** with
`PYTHONDONTWRITEBYTECODE=1` and pytest `-p no:cacheprovider`. The companion
rejects an intentionally wrong source hash; Ruff and `git diff --check` pass.
The M0/API27 commitments, A24/B34 stored-model hashes and empty review-registry
hash were rechecked unchanged. These checks do not validate future performance
or authenticate the newly inspected browser post's historical attachment bytes.

Registry validation also rejected four in-memory mutations: enabling training,
inventing an evaluation population, replacing unknown runner missingness with
zero, and changing a selected manifest hash. No source file was changed by
these negative checks. This is a bounded snapshot check, not full validation
of every descriptive field or a replacement for prospective source admission.

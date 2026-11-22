```md
# Collect bounded date-and-venue API26 scopes without altering old evidence

Maintain this living plan under .agent/PLANS.md.

## Purpose / Big Picture

Use the existing pre-race API26 collector on a fully reconciled official
calendar. Reserve one call per expected page of a date/physical-venue
scope, keep existing raw reservations when they replay, and stop the
batch on a failure without requesting the same race separately. A
scope is all the races sharing one KST date and physical racing venue.
The output is a local source receipt, not a study or forecast.

## Progress

- [x] (2026-11-22 05:45Z) Verify the preceding audit: 304 races and
  3,140 declarations matched in six archived whole blocks.
- [x] (2026-11-22 05:46Z) Create a branch in the isolated research
  checkout, preserving the original runner and collectors.
- [x] (2026-11-22 05:49Z) Pass 326 focused and adjacent cases, including
  19 for this adapter; replay all six pinned schedules without API calls.
- [x] (2026-11-22 05:51Z) Read only the rules and locations in the first
  remote secret-scan report; use the established keyword mapping for
  the two non-literal function arguments in a separate commit.
- [x] (2026-11-22 06:00Z) Replay the pinned API23 and API18 denial
  bodies as gateway code 30 without making either request again.
- [x] (2026-11-22 06:00Z) Pass 350 capture, replay, and evaluation
  tests, including simulated denials and ambiguous gateway bodies.
- [x] (2026-11-22 06:20Z) Trace the completed receipt to the fixed
  models: intake does not validate the features each scorer reads.
- [x] (2026-11-22 06:21Z) Add a no-network, whole-card input preflight
  with source and coverage checks. The 14-race synthetic card shares
  the exact same inputs with API27 and leaves every source unchanged.
- [x] (2026-11-22 06:22Z) Pass 403 regressions and the lint and format
  checks. Both original October prediction hashes are unchanged.
- [x] (2026-11-22 06:22Z) Recheck PR 141 at
  `7c36040618b92c5365014079ffaaaf9bdc7abb5a`: Python Checks, Scripts
  Checks, and API Docker Build passed; Security Checks still failed.
- [x] (2026-11-22 06:45Z) Require the original whole-card cutoff for collection,
  and both the original schedule hash and cutoff for input readback.
- [x] (2026-11-22 06:46Z) Pass 402 focused and related tests. Replay
  304 races without requests; verify five revised runner counts with
  identical cutoffs and reject substitute schedule hashes in tests.
- [ ] Release the preflight through normal review after the required
  checks clear. Keep the preflight changes local in the meantime.

## Surprises & Discoveries

The retained API26 responses can contain the entire venue/date scope
even when the request names its first race. Never assume they do: an
unexpected total, missing/extra race or inconsistent start time blocks
the attempted scope. The common provider fault code can be inside an
HTTP 200 JSON/XML envelope rather than a non-200 response.
Stored HTTP 403 responses from API23 and API18 also contain
`OpenAPI_ServiceResponse.cmmMsgHeader.returnReasonCode` in JSON.
The two archived bodies have the same SHA256
`c41369295887d9454b7f06970e62d5892fdc0c7c16cb3843a2eb20f80df4aade`.
The reported code does not establish why service-key access failed.

The repository's line-based env-file rule flagged two Python keyword
argument lines on PR 140 (CI run 44991064698). Both were code variable
references, not stored secrets. The correction uses the existing
credential-argument mapping convention; scanner rules, workflow policy
and old branch history remain unchanged.

## Decision Log

2026-11-22, Codex: Take all requested dates from the same hash-bound
national and regional capture and require that this date set equals
the actual observed schedule. Compute the first cutoff as its earliest
start minus 30 minutes. Reuse an explicitly pinned prior entry only
after a complete scope replay; do not fetch a replacement. For new
scopes, reserve the required page count from the schedule totals and
stop after the first unsuccessful scope. Protect overlapping date
windows in one canonical archive. Do not change any existing original
predictions, raw pages or approved model artifacts.

## Outcomes & Retrospective

The optional CLI is additive. It reports no independent time or study
approval and makes no calls while planning. Future real capture still
requires a complete official card and the existing authorized API
credential. Future predictions additionally require separate approval
and an actual public commitment before the first cutoff.

The earlier local scope audit (SHA256
3ff43078eb7497d25ba80eaf92fc6b47f5f74b28101a5c47f1cf0db8c398b687)
provided the six exact historical schedule and source inputs. This
adapter independently recalculated page bounds of 9, 9, 9, 8, 9, 9
on the six blocks and zero additions when each set of complete local
source pins was supplied. This was a read-only check using the prior
clock reference for historical replay, not a backdated capture.
Tests also reject a result at the exact first cutoff, after preserving
the original raw response. Both published October hashes are unchanged.

The preflight tests cover a 14-race synthetic card with 140
declarations and five intake pages, including a race found only on the
second page. API27's existing reader returns equal input rows for every
race. Reuse makes no additional requests. Null ratings remain counted
as missing; an absent field or impossible career counts block the
entire preflight. A late readback or changed pin cannot admit a card.
There was no live capture, scoring, registration, or publication.

The cutoff check replays the six archived original schedules against
their recorded cutoffs. The October 23 and November 13 blocks each
have a later, still pre-cutoff schedule with all the same race IDs
and the same cutoff, but changed advertised runner counts (three and
two races respectively). A cutoff match does not prove a schedule
match. Readback requires the original hash separately from the receipt;
neither a reissued schedule nor a later derived cutoff reopens a block.
Source revisions are separate evidence, not instructions to drop races.

## Context and Orientation

Use the separated kra-analysis-race-card-pdf checkout, Python 3.13 and
the existing virtual environment. The original API26 module is
packages/scripts/autoresearch/kra_entry_sheet_snapshot.py. Its capture
manifest and verified raw pages remain unchanged. The new module
wraps its HTTP client; it does not issue calls to other endpoints.
The historical PR #95 cohort is never rewound or replayed as live.

## Plan of Work

Add kra_entry_scope_intake.py with a read-only plan, an exclusive local
reservation, a bounded injected HTTP client, and a complete raw replay
for each scope. Add tests using httpx.MockTransport and the existing
local schedule fixture. Document the two entry points and ensure the
new tests run in the existing Python Checks job.

Add `kra_entry_scope_inputs.py` after collection. This read-only
preflight takes the path and SHA256 of a completed receipt. It replays
the pinned reservation, official schedule, and all captured or reused
sources. It checks availability of every source and completion of
readback before the earliest deadline. Collection requires the
externally fixed cutoff before any reservation or request. Readback
requires that cutoff and the original schedule SHA256 as separate
inputs. These are caller pins, not approvals. Run the unchanged M0 input
projection for each race; API27 uses the same rows. Return the entire
population with source pins and per-field missing counts, or reject
the input. A whole-roster capture can still have invalid model input,
such as an absent required field or impossible career counts. No
scoring, study approval, input reservation, or publication occurs.

Keep the existing October runner unchanged: it has its own hash-bound
implementation, dated population, source reservation and publication
rules. A new preflight cannot act as evidence of any of those events.

## Concrete Steps

    export PYTHONPATH=packages/scripts
    .venv/bin/python -B -m pytest -q -p no:cacheprovider \
        packages/scripts/autoresearch/tests/test_kra_entry_scope_intake.py
    .venv/bin/ruff check \
        packages/scripts/autoresearch/kra_entry_scope_intake.py \
        packages/scripts/autoresearch/tests/test_kra_entry_scope_intake.py

Start with the CLI plan action described in packages/scripts/README.md.
No test uses the real gateway or API key.

## Validation and Acceptance

Verify mock complete scoped pagination, zero additional requests for a
valid reused scope, denial of an insufficient budget, and no requests
for expired, duplicate, partial or mismatched dates. Distinguish
authentication, request limit, denied access, valid empty, unexpected
provider number of rows and network failures. Preserve the original
population in the local receipt and both original public hashes.

## Idempotence and Recovery

Same and overlapping calendar windows have one attempt within the
canonical archive. After an interruption, read its retained reservation
and partial raw captures. Do not delete the reservation to retry or
move the cutoff. Surviving raw files are not a substitute for a
complete final receipt.

## Artifacts and Notes

Gateway public error vocabulary: code 22 is a request limit and codes
21, 30, 31 are API-key problems. Codes 20 and 32 denote denied access.
Code 03 and an empty success do not establish that a race is absent.
On HTTP 403 inspect only one small, time-bounded error body. A known
authentication or request-limit code refines the diagnosis; code 03
does not override the HTTP denial. Never accept a mixed gateway and
success envelope as a roster.
The program retains known status and code only, never provider text
or authentication-bearing request URLs.

API26 catalog: https://www.data.go.kr/data/15058677/openapi.do
Common gateway error reference:
https://www.data.go.kr/data/15028197/standard.do

## Interfaces and Dependencies

Use httpx, existing source replay, the existing read-only official
schedule validator, and existing exclusive immutable local writes.
No new package, paid compute, training or publishing dependency.

Revision 2026-11-22 05:49Z: Record the mock tests, exact archive
coverage and the inclusive fail-closed cutoff boundary.
Revision 2026-11-22 05:51Z: Record the credential-argument syntax
correction; no real credential or scanner exemption is part of this work.
Revision 2026-11-22 06:46Z: Record the original cutoff and schedule
checks, real schedule-revision replay and scoped regression evidence.
```

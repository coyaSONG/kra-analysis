# Research decision after the fixed time repeatability audit

Keep the [PR131 time-repeatability result](2026-10-20-time-repeatability.md)
fixed. Do not extend the same 3,166 pairs with additional partial correlations,
distance windows, thresholds or selected groups. The next bounded research
question is whether **additional historical target races have complete,
version-verifiable pre-race inputs**, not whether another summary of the same
outcomes looks stronger.

## Completed consultation

The authorized Chrome ChatGPT Pro consultation completed without interruption
or a response-length limit on 2026-10-20, observed complete at approximately
19:40 UTC. The UI reported 9 minutes 19 seconds of processing. The question
provided PR131's public report and counts, missingness, fixed definitions,
known clock limitations and the prohibition on fitting, inference or future
registration. No credentials or local raw files were uploaded.

Conversation: https://chatgpt.com/c/6ad0d05d-5b08-83e8-b4b5-5252f401bb4d

The completed response was read in full. It recommended one bounded historical
point-in-time (PIT) feasibility investigation, ahead of more synthetic joint
selection work or extending unsupported venue pace semantics. Its claim to
have read public sources is not an independent verification of local originals,
the SQLite/NumPy check or model execution.

We accept the distinction between repeatability and predictive value: pace
recurrence around 0.301 and rank recurrence around 0.287 have different current
variables and cannot be compared as a feature-performance contest. Prior pace
versus current rank around -0.074 neither establishes incremental exact-set
value nor proves that all interactions are useless. None establishes a 70%
accuracy ceiling or a future improvement.

## Bounded next investigation

This is a source-feasibility proposal, not a training or evaluation protocol.
Use the existing October 10-11 pre-race archive as one positive control, not
as new data or an independent holdout. Inspect only these three paths:

1. Existing pre-race archives for unused source packets and external timing
   witnesses.
2. Official historical race-card publications with evidence of the exact
   edition available before the target cutoff and any later revisions.
3. Official API documentation for an actual historical-version facility,
   rather than a race-date filter on today's response.

Before inspecting additional target contents, record a deterministic selection
from archive metadata only: at most three additional race IDs, ordered by
race date, venue and race number, excluding already-used target sets. Do not
select by outcomes, pace availability, prediction success or field completeness.
If fewer eligible metadata entries exist, inspect fewer; do not silently replace
a failed example or broaden the budget. The three-race cap is a technical
inspection budget, not a future evaluation sample size.

For each selected target, seek the whole pre-race roster, the base input values
and observed missingness, the precise prior-history version and all associated
clocks/hash witnesses. A pace reference requires the versioned membership and
every admitted reference member's operands, not just the focal horse's record.
Do not load target top-three outcomes or model scores for this investigation.

Stop with one of: additional input path demonstrated; base PIT available but
pace PIT unresolved; evidence not found in the inspected paths; or access,
identity, integrity or clock blocker. No bulk historical download follows a
missing version guarantee. A negative bounded result does not prove that no
archive exists anywhere. A positive example is not nationwide coverage or fit
approval. No new generic registry is required.

## Source roles and execution boundaries

The [official API26 description](https://www.data.go.kr/data/15058677/openapi.do)
reviewed during this turn lists entry fields and date queries but did not
establish retrieval of an immutable historical as-of version. This is a limit
of the reviewed documentation, not a claim that the provider cannot have such
an archive. Failed authenticated queries would not settle that question.

October-acquired historical outcomes may be candidate history for a later
future cutoff. They are not automatically the original pre-race covariates
for those historical races. Removing rank/time columns from result rows does
not recover a missing pre-race roster or value version. A documented missing
value inside an available pre-race packet is different from missing evidence
of what the packet contained.

When historical PIT cannot be demonstrated, preserve all inputs for actual
newly published schedules through existing bounded collectors. Subsequent
outcomes belong in a separate versioned source; never rewrite the pre-race
packet. Collection alone is neither independent evaluation nor training
permission. The [A24/B34 preregistration draft](2026-10-20-condition-preregistration-draft.md)
remains a draft: dates, actual N and population unset, execution registry empty.
Stored models, one-fit receipts and M0/API27 commitments remain unchanged.

The concrete collector improvement in this turn is
[API26 availability diagnostics](2026-10-20-entry-availability-diagnostics.md):
retain safe observed failure categories rather than interpreting a failed or
empty response as no races. This is operational evidence, not model progress.
The bounded historical PIT investigation above has not yet been executed.

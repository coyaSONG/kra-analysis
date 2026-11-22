# Whole-card readback for the witnessed daily workout edition

This audit makes the [November 22 source clock](2026-11-23-daily-workout-edition-witness.md)
actionable when the next complete entry packet is independently witnessed.
It does not reopen any prior cutoff, admit model inputs, or register a
study. The fixed M0/API27 freeze and publication take priority.

## Evidence and time boundary

First rehash the raw index, group and all-detail responses and their
receipts from all three menus. Recreate the safe form fields, complete
horse-ID projection, and held clock values. Compare that projection
with the independently published private packet fingerprint, replaying
the exact retained GitHub response rather than accepting a timestamp
from a flag. The local readback verifies all 1,628 distinct horse IDs
and one held clock. The last observed response is
2026-11-22 19:37:02.534697 UTC; the PR #176 server witness is
2026-11-22 19:43:36 UTC. They do not establish first publisher access.

The original November 20-22 local archive contains 51 races and 540
declarations, with first cutoff 2026-11-20 01:15 UTC. The new edition
fails the clock comparison against that cutoff. No overlap was measured
or backdated for that older card. A new actual complete, independently
witnessed entry packet is still pending.

## Diagnostic and verification

Call the [existing entry witness and this readback](../../packages/scripts/README.md#일일조교-자료-연결-진단)
on the original complete card and before its first cutoff. Both the
workout and entry witness must be available at the audit time and
strictly before that cutoff. The duty to complete approved predictions
before the cutoff is separate.

The program replays the raw API26 declarations, checks every race and
runner count against the input witness, then compares stable horse ID
and exact name. It keeps clock, name and source-menu conflicts distinct
from no entry in this edition. Yeongnam is one source menu for Busan and
Yeongcheon; the final physical race venue comes from the frozen card.
Exact sample age and previously unknown distance and class stay visible.
It reports how many entire fields link, and how many also vary in
duration, without exporting numerical durations or making picks.

A synthetic witnessed card spans all four physical race venues and all
40 declared horses. The tests cover lost races, lost or duplicate
identities, late publication and completion, missing context, a
different menu, a name conflict and an inconsistent clock. A second
set reconstructs the synthetic source from its raw bytes and rejects
changed bodies, a mismatched note and a publication before collection.
These tests verify the audit, not a real new card or predictive effect.

No network request was made to KRA or the public-data API. No results,
model fits, forecasts, replacement cutoffs, or feature approvals were
produced. Once the official complete card is available and the fixed
pair is protected, run this exact diagnostic before considering a
separately reviewed addition on a future whole population.

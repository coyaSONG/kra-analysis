# Limits of repairing the original exact trio

Across the unchanged 50-race October 16-18 block, combining only
horses chosen by M0 or API27 cannot recover a single observed target.
Allowing at most one replacement per race from whichever of the two
original trios is more favorable reaches no more than 25 races,
even with perfect hindsight. The reference for 70 percent on this
population is 35 exact successes. These are limits of specific
restrictions, not attainable scores, forecasts or independent
tests of a new model.

## Published input and result boundary

The [original paired comparison](2026-10-18-full-block-paired-results.md)
remains 0 verified hits and 50 verified misses for each model, no
pending or undefined targets under its selected source version.
This replay does not change that result or imply that a later
official correction is impossible.

Read the 100 saved prediction packets and their observation records
by the exact [PR #95](https://github.com/coyaSONG/kra-analysis/pull/95)
hashes. Original linear scores, gate and stable horse ID reproduce
each saved trio without rerunning a scoring model. Replaying the
same official result plan with the original code reproduces the
selected 50 target sets. Join all 534 declarations to the exact
[separate PDF source audit](2026-11-23-pdf-tip-rating-reach.md).
Those PDF bytes are bound after the original paired prediction
publication and before its first cutoff. They are not retroactive
inputs to either model.

## How many changes were necessary?

Each column counts original races. A change replaces a horse; a
change of order does not count. For the two-model union, the count
is of true target horses that neither model selected.

| Reference | 0 | 1 | 2 | 3 |
| --- | ---: | ---: | ---: | ---: |
| Replacements from M0 | 0 | 23 | 22 | 5 |
| Replacements from API27 | 0 | 21 | 23 | 6 |
| Fewer replacements from either model at each race | 0 | 25 | 20 | 5 |
| True target horses outside both published trios | 0 | 26 | 19 | 5 |

Even with a hindsight choice of baseline at each race, any 35
correct answers would have required at least ten races with two or
three replacements. This rejects restricting the research candidate
to the two original trios or to one edit per race on this block.
It does not estimate a future error distribution.

## Can the printed columns support direct replacements?

Pair each true omitted horse with a distinct incorrect original
pick. An eligible pair must have two printed values in the same
typed column. The more restrictive variant also needs at least
one column favoring the omitted horse: lower early/late value or
higher speed index. Here a different column may disagree without
vetoing the change, so the rule deliberately overstates the chance
of an actual repair. Ties and unknown values supply no favorable
direction. The test allows any number of replacements, while
requiring that all necessary pairs be distinct.

| Starting point | Complete pairing with any comparable values | Complete pairing favoring the omitted horses |
| --- | ---: | ---: |
| M0 | 13 | 7 |
| API27 | 13 | 7 |
| Either arm, chosen with hindsight at each race | 15 | 8 |

This is not a ceiling for a model that uses the printed operands
alongside other pre-race information across the full field. It rules
out relying solely on these direct comparisons to patch an original
trio. Carry the three literal inputs and missingness separately,
and keep all declared runners in scope for a later comparison.
Choose no feature weights, cutoffs or search depths from this
diagnostic. Develop only with frozen eligible data; independently
test any selected new method on a different, preregistered complete
future population with one exact unordered trio per race. The
unchanged timely M0/API27 follow-up remains the immediate priority.

## Reproduction

Local evidence: `exact-repair-reach-20261123/repair-reach.json`.
SHA256: `64699032d04ff9bf9f358f102b349a553a3ad1d4744fb0568920728d38e9da8a`. The replay records original
source hashes, the exact result version and every race's matched
counts. A second implementation enumerates full assignments and
verifies every race, with all 100 prediction packets rehashed.
The 139 focused and regression tests and Ruff checks passed.
No race/API request, score calculation, fitting, new forecast,
publication-window change or model promotion.

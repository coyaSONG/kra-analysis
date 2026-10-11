# Versioned Result Observations

The outcome adapter retains all **50 scheduled October 9-11 races / 510 API
rows** and finds a unique unordered three-horse result in **49** selected
API/official-page version pairs. The remaining race, October 10 Seoul R1, has
11 API rows annotated as void and blank official ranks and times. It stays
`void_reported_no_top3`, not an excluded race or a certified settlement decision.
**49/50 is not model accuracy. No predictions are compared or scored here.**

## Observation Contract

`packages/scripts/autoresearch/versioned_result_observations.py` is additive.
It replays the selected API seed, original raw responses, official archive
manifest, receipts and HTML. The dated national schedule defines the population.
There is one ledger row per scheduled race, including absent sources and source
conflicts. Unexpected races on the selected dates are listed separately. Results
outside those dates remain outside this explicitly declared observation scope.

`unique-ranks-1-2-3-whole-roster-v1` requires the same dated physical event,
exact equality of the complete gate/horse sets, agreement on every ranked
runner's rank and elapsed time, and exactly one matching horse in each of ranks
1, 2 and 3. It rejects unresolved API runners that have a nonblank official
finish. Raw duplicate API top ranks cannot disappear through status filtering.
The resulting three canonical horse IDs are sorted numerically, not lexically.

A lower-ranked exception with blank official rank/time does not erase the
otherwise unique observed top three. The original API record, note, unresolved
status, official row, source receipt and raw hash remain in the report. This is
not verification of the exception's official meaning or eligibility. The **9
national schedule runner-count differences** remain visible; they are not
rewritten to match the later result roster. This adapter does not weaken M0's
pre-race input checks.

Ties affecting the top three, including those for which a set might be uniquely derivable
under some rule, remain unresolved by this deliberately narrow observation
policy. Lower-rank ties do not automatically invalidate a unique top three.
Void notes do not establish a KRA settlement decision. Corrected source
versions produce separate reports; neither version silently replaces the other.
Source corruption is an error, not a missing row that may be quietly discarded.

## Actual Replay

The frozen seed contains 6,816 rows over 671 observed events. All source pins are
replayed, then the declared dates select 510 rows for the 50-race schedule.
No extra API or official race IDs appear on those dates. The prior API-only
37 ordinary / 13 review classification remains nested in the per-race diagnostics;
it is not an evaluation population. Twelve lower-rank exception races can now
have a unique observed top three while retaining their exception evidence.

From the isolated research checkout:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.versioned_result_observations \
  --plan .cache/autoresearch/versioned-outcomes-20261012-plan.json \
  --plan-sha256 314056646885d6112bbd392dcd7f8a20c2a934b03b6ab788090a270ee02be898 \
  --output <new-report-path.json>
```

Paths in this local plan resolve from the checkout working directory. Output
publication is atomic and exclusive; an existing report cannot be overwritten.
Exit zero means replay completed, not that all outcomes or predictions are valid.

| Source | SHA256 |
| --- | --- |
| National schedule capture | `08fe1bb58be2a394476158e8a52697a2ae2e77c9e1bf6084b1e11972fae3a7c7` |
| Frozen API seed | `0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66` |
| Official HTML archive | `eaece57cdd27ee4e348e171e04368440da9d82a4417110476f0a1a1400e934e2` |
| Observation plan | `314056646885d6112bbd392dcd7f8a20c2a934b03b6ab788090a270ee02be898` |
| Initial report, versioned-outcomes-20261012-v1.json | `a628d93e8ceedbadd61a57a782d0de891e383fe0e1173e8b6a7f075ed241953c` |
| Final report, versioned-outcomes-20261012-final.json | `86b88464eaf8b40ba0f55c1af9ba06a158d93adbaea0b25a47dfb44f3881a071` |
| Observation policy | `389f4cffa53f5e7172383aa9e452fd53cf8afeb6091a4728379cb8b2e8a3bd28` |

The report lives in the ignored `.cache/autoresearch` directory. It includes
the adapter source hash and the full source plan, so a later implementation or
source selection is visible rather than an overwrite of a historical claim.
The final report adds a source-derived observation ID per race, policy hash,
and parser/replayer source hashes. These IDs are local research identifiers,
not publisher revision IDs; the latter remain null. Source clocks are retained
as local observations, not independent timestamps. The initial report is preserved.

Focused regressions pass **175 tests**, including **22 new cases**. Ruff lint,
format and diff checks pass. The new CI step uses the existing Scripts environment
and adds no dependency. Remote check results are recorded on the PR.

## Limits and Next Evaluation Step

The original full M0 was fitted after these historical targets. Therefore this
adapter accepts no prediction file and emits no success count, rate or confidence
interval. Its `counts_as_70_percent_evidence` remains false because outcomes alone
cannot establish prediction success, not because future evaluation is impossible.

The canonical `local_m0_20261016_18_v1` inference contract was compared against
its saved JSON and remains unchanged. No model was fitted, promoted or selected
from this outcome replay; no paid service was provisioned.

The next scoring adapter must independently replay the frozen future population,
the occupied prediction slots and their timing evidence, and a prospectively
declared outcome-version/correction policy. It must retain missing predictions,
unknown outcomes, ties and voids in the complete denominator. An ordinary-only
or known-result-only success rate cannot substitute for the 70% goal.

KRA's [void-race explanation](https://race.kra.co.kr/raceguide/RaceFailureRaceService.do?Act=05&Sub=3&meet=1)
says placings are not recognized after a race is declared void, even if runners
crossed the finish. This does not prescribe a binary research score for such a
race. Blank HTML ranks alone do not prove a void declaration. The adapter separates
explicit API void text from unexplained blanks and rejects void/finish conflicts.
It does not extract an event-level HTML declaration or settle a wager.

## Completed Pro Review

The authorized [Pro consultation](https://chatgpt.com/c/6aca2dc4-d2e8-83e8-acab-e85f281c27b7)
completed with the UI showing **9m 1s**. Its full answer was read only after
completion; generation was not interrupted. Pro inspected public PR82 and supplied
facts, not our local raw files. It recommended the outcome path before new feature
research, whole-roster observation separate from finality, explicit void/missing
states, raw top-rank ambiguity checks, and immutable observation versions.

This increment intentionally implements only its outcome-replay half. Full future
prediction evaluation and correction scheduling are not claimed complete. The
future collector must derive requests from the frozen future universe, not the
existing history seed or the subset of available results. A prospective outcome
observation/correction policy must be bound separately to the existing PR82
contract without replacing that contract.

For that later evaluator, retain confirmed hits, confirmed misses, pending
evidence and undefined targets separately. Only a known complete population
permits a denominator. H/N and (H+Q)/N bound missing binary evidence only when
every target is defined; they are not confidence intervals. Voids and unsupported
tie semantics must not be silently treated as missing 0/1 labels or removed.
No such counts or bounds are computed from this retrospective replay.

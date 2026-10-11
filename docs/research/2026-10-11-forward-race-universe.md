# Official full-race universe: source milestone

## Finding

The dated national race list and all three regional dated lists can be reconciled from retained original HTML. This is source and software validation, not a future prediction or accuracy result. The target remains 70% exact success for one unordered three-horse prediction on every race in the complete frozen universe.

At capture time, the official cards covered October 9-11, 2026. The requested October 16 date was not published in these sources. No future candidate, prediction submission, model training, promotion, or 70% result was produced.

## Official sources

- [National dated list](https://race.kra.co.kr/thisweekrace/ThisWeekDetailInfoList.do): 50 race rows across October 9-11. Selling-venue columns are not additional races.
- [Seoul dated list](https://race.kra.co.kr/chulmainfo/ChulmaDetailInfoList.do?Act=02&Sub=1&meet=1): 21 rows.
- [Jeju dated list](https://race.kra.co.kr/chulmainfo/ChulmaDetailInfoList.do?Act=02&Sub=1&meet=2): 14 rows.
- [Yeongnam dated list](https://race.kra.co.kr/chulmainfo/ChulmaDetailInfoList.do?Act=02&Sub=1&meet=3): 15 rows, comprising nine Busan races and six Yeongcheon races. Menu code 3 does not imply physical venue 3.
- [Undated weekday timetable](https://race.kra.co.kr/thisweekrace/ThisWeekBaljuTime.do): inspected separately, not part of the new capture/admission path. Seoul race 10 was 17:25 there but 17:30 on both dated lists. Do not infer a future date or change a deadline from this undated table.

These are observations of mutable official pages at the capture time, not permanent calendar facts. Both dated presentations belong to KRA; agreement is a cross-check, not evidence of independent clocks or an independent publisher.

## Retained evidence

Local ignored bundle: `.cache/autoresearch/forward-schedule/20261011T100723.518882Z_a349dc8395f0/`. All four raw files are EUC-KR HTML. `capture.json` SHA-256 is `08fe1bb58be2a394476158e8a52697a2ae2e77c9e1bf6084b1e11972fae3a7c7`.

| Source | Bytes | Capture completion (UTC) | Raw SHA-256 |
| --- | ---: | --- | --- |
| national | 97211 | 2026-10-11 10:07:23.752150 | `9175cc3b8a997f4effa61cfc0adccad10acbf8b8844b453a296b315e9d06aea5` |
| region_1 | 65350 | 2026-10-11 10:07:23.777731 | `56e6507892f6769393bbffe9470b9539b225642360b0d87b65579109a8f3c326` |
| region_2 | 52780 | 2026-10-11 10:07:23.801993 | `c11a2b93d4709791c3fc1b84d0c0533ff0cf2ac679d71bb5a71bc96174f00c22` |
| region_3 | 54949 | 2026-10-11 10:07:23.826601 | `42a1acb2a391f09d125c2eba6e80b481324733b51863723aeecf64a9b9cb5e2d` |

The source HTTP Date was 10:07:23 GMT. It is retained as diagnostic metadata, not an independent certificate that commits to the captured bytes. Local capture timestamps and hashes likewise do not establish external preregistration.

## Implemented behavior

`shared/kra_schedule.py` parses explicit table structure, validates dates/weekdays, physical venues, row ordinals, unique race keys, contiguous race numbers and current runner counts. It preserves source observations and cancellation notes. The entire published week is reconciled before selecting the requested date; even a conflict on another date blocks admission.

`autoresearch/kra_schedule_snapshot.py` captures exactly four public URLs without credentials or redirects, bounds each response to 5 MiB and each whole request to 30 seconds, and validates a maximum 300-second capture window. Complete original files and the manifest are published without replacing existing files. HTTP/parser failures cannot certify a partial race population.

Replay verifies exact original bytes against their hashes and sizes before parsing. A missing future date is `unknown`, not a complete empty day. Local freezing requires all sources to reconcile and actual local time to precede the earliest race's fixed T-30-minute feature cutoff. Output explicitly says `pending_independent_server_receipt`, `independent_time_verified=false`, and `target_accuracy_verified=false`. There is no CLI clock override, though local clocks/files are not tamper-proof.

## Actual replay and rejection results

- October 11: `reconciled`, 17 races (11 Seoul, six Yeongcheon), no source failures or reconciliation issues. Freeze rejected with `universe_must_be_frozen_before_earliest_cutoff`; this capture is post-race.
- October 16: `unknown`, zero known target rows, `requested_date_not_published`. Freeze rejected with `universe_requires_complete_reconciled_official_cards`.
- Neither rejected freeze created a candidate file. Historical originals are retained only as source/parser evidence.

## Verification and remaining work

Local source, identity, entry-sheet, and training-admission regressions: **179 passed**, with 15 existing joblib/NumPy deprecation warnings. Focused cases cover every physical venue, source/member/time/count conflicts, malformed/truncated/empty HTML, bad clocks/pins, altered originals, symlinks, redirects, non-HTML/oversized responses, slow streams, late/backdated freezes, and existing-output preservation. Required Python CI now includes the focused schedule cases. Synthetic successful freezing demonstrates software behavior only.

PR #68 merged normally at 10:21:33 UTC as `472f005dfc342d3691eea0c3ae45b0bce1f7e9eb`, after required Python Checks, Scripts Checks, PDF tests and Docker build passed on `5e30bbc72094951d09ee6c8b02f05ddc918426d8`. The separate Security Checks failure contains the same 17 dependency records in h2/multidict/pyjwt as the existing baseline. Gitleaks passed; later Node audit/hygiene steps were skipped, not verified. No check or protection was weakened.

## Completed Pro consultation

The authorized Pro model was asked at approximately 09:57 UTC. At 10:22 UTC the browser showed response completion and a 20m 40s processing duration. The full answer, including its final independent-research recommendation, was read only after generation ended. No short response deadline or stop action was used. This is methodological advice, not a rerun of our tests or an approval of production data.

The request preceded discovery of the national dated list. Pro's date-binding concern about the undated weekday table therefore does not invalidate the newer dated national source. Pro also reported a later 17:30 observation in the undated table, unlike our earlier 17:25 observation. That report is not a locally retained raw revision; the timing/cause of any change is unverified. Preserve the earlier observation rather than retroactively rewriting it. The implemented dated sources agree at 17:30.

Adopt these boundaries for the next increment:

- Use one deterministic roster B0: numeric starting-number order, exactly three distinct stable horse IDs from a qualified same-race roster, no historical prediction lookup. Preserve its input as-of and code/source hashes; this weak rule is an operational control, not the claimed best model.
- Freeze study/arm and full membership before predictions. Keep membership, schedule, roster, registration, timing and outcome status distinct; failures never remove a race.
- Prefer the existing API/PostgreSQL to mutable GitHub comments as the primary receipt store. Use a unique study/race/arm slot, not a key expanded with changeable universe/model/input hashes.
- Lock an existing frozen membership row, compare existing full canonical payloads for idempotence/conflict, read `clock_timestamp()` after the lock, enforce the server-stored deadline and explicitly commit.
- On a separate connection/transaction, read the committed payload first, then record `committed_visible_observed_at`. Reject observation in the writer transaction, including savepoint-only separation. This proves visibility by the observation time under the trusted server-clock model; it is not an exact commit timestamp.
- Missing timely observation is timing unproven, not proof of actual late submission. Preserve the original payload/receipt on retries and response loss. An identical retry after the deadline may retrieve an existing timely receipt; it must not create a revised prediction.
- Test on actual PostgreSQL: competing same/different payloads, lock wait across deadline, delayed commit, same-transaction observation, rollback, lost acknowledgements, forbidden runtime mutation, full-population joins and corrected outcomes.
- Verify deployed primary/version/runtime privileges/clock operations/durability before a real study. Runtime insert-only restrictions do not make records immune to DB-owner changes. Do not describe the MVP as external notarization.

The next operational deliverable must connect collection, freeze, B0 execution, registration, receipt read-back and every-race reconciliation in an executable command. A table or empty registry alone is not completion. Current source-only implementation is not yet that operational path.

Independent research recommendation: compare the stored strict-fallback and structured-ranker predictions on exactly the existing October 116-race development universe, using the original corresponding labels. Recompute paired exact hits and inspect omitted/extra horses and input missingness. Do not retrain, regenerate old predictions, reuse December for selection, or infer future 70% performance. Use the result to choose one falsifiable information hypothesis.

This bounded diagnostic was subsequently executed from pinned saved inputs; see [paired errors and the rest-interval hypothesis](2026-10-11-october-paired-error-audit.md). It identifies a feature-semantic concern but does not establish a new model's accuracy.

No production database migration or credential-dependent operation was performed in this increment. B0, server receipts, and actual future records remain unfinished.

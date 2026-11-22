# Jeju weekly nomination report

Jeju weekly nomination evidence SHA256: `5134f473f4a2bb88fae7e53dfcdb46572cb10b10f8f2500a233b3c19deed07d5`.

This is an official source observation, not a frozen race card, a
verified starter roster or a model result.

## Source and observation

The [Jeju text archive](https://race.kra.co.kr/dbdata/textData.do?Act=12&Sub=1&meet=2)
listed ten Saturday editions on the captured first page. The
November 18 filename tested from the mainland pattern was not on
that page. The observed November 21 link selected the only file read:
[20261121dacom07.rpt](https://race.kra.co.kr/dbdata/fileDownLoad.do?fn=chollian/jeju/jungbo/chulma-horse/20261121dacom07.rpt&meet=2).
The report body, not the filename, places every printed field in
physical Jeju on November 27 or 28. Provider first publication is
unknown. The known clocks are the actual completed collection times.

| Saved HTTP 200 response | Collected (UTC) | Bytes |
| --- | --- | ---: |
| Nomination archive listing | 2026-11-22 18:11:39.741913 | 33,282 |
| November 21 report | 2026-11-22 18:12:33.721362 | 23,171 |

Report raw SHA256: `981f550fe2cc2fd691e3447c871771277c2fa23e5e5174efd7b22027f477f7bb`.
Listing raw SHA256: `83b2f053bb702682a4f9a6bca5b6f60535b90e75adcea041468550d2864367fb`.
The two calls used the existing bounded collector. Neither used
credentials, redirects or retries. No schedule, public-data API or
result was requested for this observation. Receipts, source links,
exact bytes, row locations and prior comparison sources are bound
locally by the evidence digest above.

## Coverage and join limits

| Body date (KST) | Printed race numbers | Nomination rows |
| --- | --- | ---: |
| November 27 | 2 through 7 | 95 |
| November 28 | 2 through 6 | 72 |
| Total | 11 preliminary fields | 167 |

All ten fields from the saved [earlier nomination first page](https://race.kra.co.kr/chulmainfo/RegistStateList.do?Act=02&Sub=6&meet=2)
match on physical race key, grade, distance, weight rule and row count.
The report also covers November 27 race 2 (13 rows), not observed on
that earlier first page. Other pages of the earlier list were not
collected. This is additional observed coverage, not proof of a newly
scheduled race or the absence of other races.

November 27 race 3 has 14 unique same-race name pairs and 14 equal
printed ratings against the earlier [web detail](2026-11-23-preliminary-nomination-witness.md).
The weekly report prints a registration number, not a gate or a
stable horse ID. It confirms zero stable-ID row joins. A name and
rating match at nomination is not a final declaration or a starter.
The report does not supply the web detail's last-start date or
3-, 5- or 7-appearance rank fields.

No printed rating, six-month earnings, one-year earnings or career
earnings field is blank. Respectively 21, 8 and 0 of the three
earnings columns print a literal zero. They are not missing values.
The report does not independently define the timestamps or inclusion
rules for its earnings windows; those totals are not assumed to be
API26 equivalents or mainland recent-appearance prizes.

## Next Check

All 11 fields have at least one group of equally rated horses with
different printed six-month earnings. That variation makes the
separate source worth testing; it is not evidence of predictive lift.
First verify the complete official card and its original cutoff,
validate identity within each final race with stable IDs and
corroborating evidence, and record withdrawn, added, ambiguous and
missing rows. Only then consider a fixed within-race earnings contrast
against the unchanged baseline on a separately registered full
future population, using distance and grade for diagnostics only.
Do not fit or score this unregistered set or alter M0/API27.

Local packet: `jeju-nomination-saturday-20261123/weekly-nomination-evidence.json`.
Independent raw parsing reproduced the row and zero counts and the
14 name/rating pairs. The related local suite passed 122 tests.

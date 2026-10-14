# October 16-18 prospective prediction publication

## Scope

The previously declared national October 16-18 block now has complete official
race membership. The original M0 collection command reconciled the national
card against all regional cards and froze the same canonical series without
changing its model, source selection, deadlines or population rules.

| Date | Races | Declared runners | Meets |
| --- | ---: | ---: | --- |
| October 16 | 16 | 170 | Jeju, Busan |
| October 17 | 17 | 178 | Seoul, Jeju |
| October 18 | 17 | 186 | Seoul, Yeongcheon |
| Total | 50 | 534 | All published national races |

The first block cutoff is **2026-10-16T01:20:00Z**, or 10:20 KST.
Population freeze times were October 14 at 06:17:28.620009Z,
06:20:18.968479Z and 06:24:00.503877Z respectively.

Earlier October 14 observations remain preserved: the 05:15Z card only exposed
14 Jeju races and mixed old regional weeks, so it did not establish the complete
national population. The separate 137-row early Jeju capture is diagnostic and
does not replace the original M0/API27 input reservations.

## Completed Local Execution

M0 completed all 50 predictions and readbacks at 06:27:36.039760Z on October 14.
API27 completed all 50 using the same reserved inputs at 06:27:50.073480Z.
The separate learning-input run sealed 50 packets / 534 runner rows with 24
columns, all locally timely, and completed at 06:28:11.171335Z. Neither model
was refitted. No target outcomes were collected.

Exact-byte files in `commitments/2026-10-16-18/`:

| File | SHA256 |
| --- | --- |
| `m0.json` | `de82b4d1dc1d69b7982af04b7d83557d008381ea23202f0dff661721388f7a2c` |
| `api27.json` | `a51f7b8ca425251fa6bc7602788031a6675b3b9de195c55db76789d5847f6646` |
| `training-inputs.json` | `b4ab302c93bb01a947bd149622770d3413690f5fa95bbec8c13a00ed2808fa32` |

The prepublication read-only evaluation replayed the whole local block. Its
only population issue was the then-unproven pre-cutoff external publication.
Both arms retained 50 pending targets and null accuracy, with no paired success
table. Report SHA256:
`6f1555d571b6504c752fe07c8076a2dd8a92add098715f7aa0d93613cdcbb4e2`.
The report is in `.cache/autoresearch/forward-publication-20261014/`.

## Evidence Policy

The exact selected M0 and API27 commitment files must be published together.
API27 uses the original shared M0 intake and its own fixed preprocessing/model.
The 24-column training-input manifest is a separate artifact, not a new model.
No source raw pages, credentials or target labels belong in this publication.

Local capture and readback do not by themselves prove external publication.
After normal checked PR merge, the existing read-only evaluator must fetch the
live merge metadata and exact commitment bytes and verify the pre-cutoff bound.
Neither this narrative nor an open PR substitutes for that witness.

There are no outcomes or accuracy estimates yet. The 70% single unordered
three-horse exact-match goal is unachieved. Missing, invalid and unresolved
records must remain in the full population; no subset, portfolio or top-k
metric replaces that objective. No model fitting or promotion is performed.

## Validation

Before publication, the unchanged existing code passed 328 focused tests:
116 M0, paired API27 and prospective-input tests, plus 212 official schedule,
entry capture, hash witness, condition projection and API27 admission tests.
Remote CI status and merge witness are separate from these local test results.

The fixed protocol details remain in `2026-10-12-local-m0-forward.md`,
`2026-10-12-api27-forward-pair.md` and
`2026-10-12-prospective-training-inputs.md`.

# Pre-Race Public Hash Commitment

## New Evidence

The October 10-11 source archive is not limited to local clock evidence. A live
GitHub REST read confirms that [PR61](https://github.com/coyaSONG/kra-analysis/pull/61)
merged at **2026-10-09T17:08:16Z** as
`f794ffc24414117420004ca45bd8ae20a04385db`. The document in that exact immutable
tree, not today's branch or an editable PR description, contains these hashes:

| Artifact | SHA256 |
| --- | --- |
| Input plan | `0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0` |
| Feature bundle | `8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6` |

The actual local files match both hashes. Replaying their original PDF/API26
chain verifies **28 of 28 race source chains**. The merge time precedes every
captured scheduled T30 cutoff, earliest `2026-10-10T10:05:00+09:00`.
The original **27 source-eligible races / 282 feature rows** reproduce exactly.
`20261011_1_8` retains its incomplete/name-mismatched join and no feature rows.

This is positive content-existence timing evidence under the explicit trust
model below, not a training approval or predictive result. No acquisition time,
source value, original plan, blocked race or original implementation was rewritten.

## Claim and Trust Boundary

Trust GitHub's authenticated HTTPS service metadata, its mapping from the merged
commit to the contents response, and cryptographic preimage resistance. Under
those assumptions, the fixed artifact content was committed by the server merge
time. The Git blob hash additionally checks the retrieved document bytes. Local
Git author/committer dates, local file times, current branch heads, mutable PR
bodies and comment creation times are not used as publication evidence.

The [GitHub pull-request API](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request)
exposes the merge event and commit. The [contents API](https://docs.github.com/en/rest/repos/contents#get-repository-content)
allows retrieving a document at that exact reference. The audit retains both
raw JSON responses and decoded document bytes with current retrieval times and
hashes. A saved response alone is not a cryptographically signed GitHub receipt;
the CLI performs live public reads, and later reviewers can independently repeat
them. GitHub service compromise and adversarial collector fabrication remain
outside the established guarantee.

GitHub does **not** authenticate KRA's response provenance, prove the precise
HTTP acquisition time, prove that this was the last roster before the deadline,
prove actual start times, freeze a national race universe, or register a prediction.
Official-source provenance still relies on the original HTTPS collector and its
retained request/response chain, checked against the fixed source contract.
Do not label this a trusted timestamp authority or universal notarization.

The [API26 catalogue](https://www.data.go.kr/data/15058677/openapi.do) describes
pre-race runner information and real-time updates. That is not a provider promise
of immutable historical versions. Today's historical downloads remain different
from this genuinely pre-race committed capture; the newly verified bound does
not rehabilitate the unapproved 2025 corpus.

## Reproduction

From the isolated repository root with the PDF extra installed:

```bash
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.prerace_hash_witness \
  --plan .cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/input_plan.json \
  --bundle .cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/feature_bundle.json \
  --archive-root /Users/coyasong/Developer/coyasong/kra-analysis \
  --output-dir .cache/autoresearch/prerace-hash-witness
```

The public GitHub reads need no token. Each run creates a new directory containing
`pull.json`, `document-response.json`, `published-document.md` and `report.json`.
Exit 0 means at least one source-review candidate, not that all races are usable
or training is approved. No result or model artifact is read by this command.

Initial actual run: `20261011T121024.190941Z_1f0a6666f3f9/report.json`, SHA256
`349d24548a3d6bc7e963d287beceb9d19b92e15478455e90cc571232abd49769`.
The document SHA256 is
`f82dacb7132d871af231fa147152bef96445d16a5223e6cc4e9f7abfcdafeda7`,
Git blob `37daf6e3a6cb423454950646a156b94eee55f8bd`.
Final implementation replay:
`20261011T121531.534487Z_c6c93a9ac319/report.json`, SHA256
`9602f990e59853ef9d105bd9dbc622ddffaf9940a1931a581e84a7b51138d94a`.
It independently re-fetched the same public response bytes and reproduced the
same 28/27/282 result. The audit script SHA256 is
`349a7028444ff349ddef4d28fffb6159ff71e2bb42243a589f40366efb85b16d`.

The old implementation fingerprint differs from current main. Both fingerprints
are recorded; current raw parsing and the original exported projection agree.
This audit does not bypass the original bundle export's implementation-drift
guard or replace its plan fingerprint. A later training recipe must pin its
actual current feature transformation separately.

## Training Boundary

The inventory contains 28 races, but it is not the complete national evaluation
universe. The original unresolved Busan scope is retained as historical context;
later official schedule investigation identified the relevant Yeongcheon card.
Neither fact adds races or feature rows to this pre-race committed archive.

Source eligibility, supervised-label eligibility and future evaluation membership
are separate. A diagnostic join to the PR73 result-observation report gives 20
races with both candidate source features and ordinary rank observations. This
is not an approved training cohort: stable-ID full-roster joins, label-version
policy, cancellations and source review remain to be completed. It must never
be used as a reduced evaluation denominator. The 28 records and all exclusions
must survive cohort construction. These dates have already been inspected and
cannot be relabelled an untouched holdout.

Production approved recipes remain zero; no model was fitted or promoted. The
next useful step is an explicit candidate-corpus join and source/label review,
then one fixed small structured baseline/PDF ablation for later full-universe
forward comparison. This evidence does not justify unbounded Laya/selector
searches or a claimed 70% rate.

## Verification

The focused witness suite passes 28 tests, using actual synthetic PDF/API parser
replay rather than only approval flags. The broader source/result/training
regression suite passes 462 tests with 15 existing NumPy/joblib warnings. New CI
runs in the PDF-enabled Scripts job so dependency-based skips do not hide those
cases. No dependency, production registry, forward-registration code or model
changes are made.

For PR73, the 65 PDF skips in the API environment were independently resolved:
Scripts job `114464407454` installed the PDF extra and passed all 70 replay/bundle
tests. That was not an async-coverage gap, and no repair to that job was required.

## Pro Review

The selected Pro model is reviewing this new evidence question. Do not treat
its in-progress observations as a completed consultation or source approval.
Final advice will be recorded after the generation finishes without interruption.

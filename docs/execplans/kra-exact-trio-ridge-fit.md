# Fit a full-field exact-trio objective in a controlled rehearsal

Maintain this plan under `.agent/PLANS.md` in the separate research
checkout. Follow `docs/execplans/kra-walk-forward-fold.md` for source
chronology. This plan adds a numerical component, not a study approval.

## Purpose / Big Picture

Sorting three individual inclusion scores need not choose the most
likely unordered three-runner outcome. Make it possible to fit one
set-level likelihood with equal weight per declared training race,
then select a single mode on a separate complete field. The actual
source population, cutoff, held-out outcomes and approval stay outside
this numerical function. It receives no files, races to collect, or
evaluation results. Its executable verification uses fictional cards.

## Progress

- [x] (2026-11-22 22:17Z) Inspect the existing complete-field
  distribution, actual saved October accounting, and chronological
  private packet. Confirm the separate runner authority and the lack
  of additional admitted complete weeks.
- [x] Implement the standard-library accounting and one SciPy solver
  call with an independently re-evaluated stationarity check.
- [x] Test known synthetic solutions, exact frozen roster joins, and
  a separated future synthetic selection without reading its labels.
- [x] (2026-11-22 22:32Z) Read completed Pro design review and
  reconcile its test and boundary recommendations.
- [x] Verify the old runtime fingerprint against the baseline.
- [ ] Verify the remote required checks and ordinary merge in the PR.

## Surprises & Discoveries

The existing distribution already provides exact-set losses and
gradients for both all alternatives together and a fixed partition.
In the partitioned version the baseline group masses are invariant;
this is a restriction, not a cure for selective missingness. More
general separately fixed margins are a different, nonconvex objective.
Adding a softmax to the same sums of runner scores does not change
which three win the numerical comparison with an additive base and
one full-field normalization. A duplicated additive feature can
still change a fitted selection by effectively reducing its
regularization, so a changed selection alone is not evidence of
nonadditive representation.

## Decision Log

Use the existing `autoresearch.exact_trio_distribution` over every
unordered triple. Require exact separately supplied race and roster
membership and exactly one defined target for each training race. Do
not downweight by number of runners or choose any column, penalty,
cutoff, model or effective population from target availability. The
feature order and positive L2 penalty are specified by the caller;
there is no fitted transformation in this component. Use a single
fixed-budget L-BFGS-B call from zero and its supplied analytic gradient.
A numerical error, solver failure, or failed final gradient threshold
does not return usable coefficients. Do not retry in another solver.

The objective is mean exact-set negative log probability plus
`penalty * ||theta||^2 / 2`. With fixed design and groups this is
strongly convex: each loss has a positive semidefinite Hessian and
the penalty adds `penalty * I`. The mathematical gradient norm
divided by the penalty bounds distance to the exact solution.
Here it is a floating-point diagnostic, not a directed-rounding
certificate of an exact optimum or its leading alternative.

The completed Pro methods review (11m 35s displayed) did not use
private data, inspect the implementation or run a fit. It supported
one future comparison using full-field normalization in both arms:
the same fixed log baseline and additive features, with just one
preregistered nonadditive term in the second arm. Freeze shared
transforms on admitted earlier cards only, including missingness and
scaling rules. A partitioned design fixes joint missing-ID group
masses and is a separate hypothesis, not a setting to choose after
seeing future outcomes. This recommendation is not a registration.
Near ties also need a separate publication rule before live use.

## Outcomes & Retrospective

The broader local regression suite passed 279 tests. A 72-digit scalar calculation
checks the coefficients, objective, and re-evaluated gradient. Unordered
member permutations and race mapping order do not change the result.
With 48 fictional target observations on equal five-runner fields, the
additive-only and single-pair-feature fits have different modes across
the same full candidate set. This establishes that the implementation
can change a selection without using a top-k shortlist. The contrast
of `(1,4,5) + (1,2,3)` against `(1,2,4) + (1,3,5)` has balanced
runner counts but differs on the pair indicator, so no sum of
individual runner scores reproduces that column. It is not a scored
validation or a proposed real feature recipe.

The existing fictional chronological fixture consumed all 28 prior
training races from two distinct full cards, then made a single choice
for all 14 races of a third card from inputs alone. Its replay forbids
the future outcome request. The test uses made-up operands and source
clocks with fictional publication receipts. No real fit or selection on
the observed October block occurred. The pull request records the
remote checks separately from this local evidence.

An independent local capacity rehearsal uses 600 fictional races with
field sizes 7, 9, 10, 12, 14 and 16. One pass through the accepted fit
considered 138,300 alternatives (8 iterations and 10 solver evaluations)
and finished in 2.956 seconds in this checkout; estimated stationarity
radius was `2.48e-9`. This measures execution of one invented design,
not expected real training throughput or predictive performance. The
local script is `.cache/autoresearch/exact-trio-ridge-fit-20261123/synthetic_capacity.py`,
SHA256 `5f63bdb69184ae13b67c457dcc22d3cbdb412363c8ad585036983fa1bfef996e`.

Compared all 210 Python source and environment paths included in the
existing fixed runtime against the baseline Git blobs; no path or byte
changed. All 41 focused and chronological cases also passed from the
API CI working directory with no special import setup. No KRA/API
fetch or released model run occurred.

## Context and Orientation

`packages/scripts/autoresearch/exact_trio_distribution.py` verifies all
unordered alternatives for one declared roster and returns a log loss,
gradient or canonical mode. `docs/research/tools/kra_walk_forward_fold.py`
binds certified earlier-card evidence and a different input-only card;
it does not train or grant authority. The fixed model runtime broadly
fingerprints non-test code under `packages/scripts`, so place the new
optional component at `docs/research/tools/kra_exact_trio_ridge_fit.py`.

## Plan of Work

Aggregate the existing race loss in canonical race order. Fit only if
all expected race IDs and all expected runner combinations agree and
every target is a unique trio from that field. Independently recalculate
the objective and gradient at the reported solution. Test that a strong
nonadditive synthetic effect can change the selected trio while a joint
probability with the same additive weights alone cannot.

## Concrete Steps

From the isolated checkout root, run the new and adjacent tests with
`PYTHONPATH=packages/scripts:apps/api` and the installed `.venv`:

    .venv/bin/python -B -m pytest -q -p no:cacheprovider -o addopts='' --import-mode=importlib packages/scripts/autoresearch/tests/test_kra_exact_trio_ridge_fit.py packages/scripts/autoresearch/tests/test_exact_trio_distribution.py

## Validation and Acceptance

Compare a small known ridge optimum with independent high-precision
arithmetic, include a group with no informative variation, and check
permutation stability, complete denominators and failure paths. Reuse
the existing numerical full-field mode, not a top-k or shortlist.
Verify focused lint, formatting, tests, the required GitHub checks and
the original October commitment bytes before ordinary merge.

## Idempotence and Recovery

The deterministic synthetic calls do not write or contact providers.
The numerical component is not an operational attempt ledger. A later
approved study must bind the exact solver/runtime/feature recipe and
separately record its single attempt, failures and timely publication.

## Artifacts and Interfaces

`fit_exact_trios` consumes explicit expected rosters, prepared
distributions, targets, feature order and ridge penalty. Its returned
state has coefficients only after successful optimization and the
final gradient check. Use a separate independently preregistered
prediction path only after approvals and genuine frozen data exist.
SciPy is already installed as part of the local research runtime; no
new dependencies or paid services are needed.

The [solver manual](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html)
distinguishes function-reduction, gradient and evaluation-budget exits.
The float64 fit starts at zero with `ftol=1e-15`, `gtol=1e-11`,
300 iterations, 1200 evaluations, 10 correction vectors and at most
20 line-search steps per iteration.
Recompute the finite objective and full gradient after success, without
trusting the solver-provided gradient. Require an estimated radius at
most `1e-5` under this numerical policy. A near tie in computed scores
is not an exact mathematical certificate; the unchanged probability
component's canonical tie order applies to equal computed scores only.
The symmetric two-label fixture has exact optimum zero. Two invented
solver proposals at `-1e-6` and `+1e-6` both meet the numerical radius
limit, but select different trios. Neither serves as a certificate of
the mode at the exact mathematical solution.

Revision: Recorded the completed methods review, added an exact
nonadditivity contrast and made the line-search settings explicit.

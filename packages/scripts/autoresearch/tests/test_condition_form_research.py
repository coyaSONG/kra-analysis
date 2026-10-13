"""Condition comparisons must retain every archived slot and original fallback."""

import json
from copy import deepcopy
from fractions import Fraction

import pytest

from autoresearch import condition_form_research as research
from autoresearch import history_form_research as form
from autoresearch import race_conditions as conditions
from autoresearch.observed_history_seed import digest, save


def header(
    grade="\uad6d6\ub4f1\uae09",
    distance="1200M",
    venue="\uc11c\uc6b8",
    date="2026\ub144 07\uc6d4 12\uc77c",
    number=1,
):
    return (
        f"<table><tr><td colspan='4'>{date} (\uc77c) \uc81c{number}\uacbd\uc8fc {venue}</td>"
        + "<td>x</td>" * 5
        + f"</tr><tr><td>{grade}</td><td>{distance}</td>"
        + "<td colspan='2'>x</td><td>x</td><td>x</td><td>x</td><td>x</td></tr></table>"
    )


@pytest.mark.parametrize("distance", ["1110M", "1610M", "2000M"])
@pytest.mark.parametrize(
    "grade", ["\uad6d6\ub4f1\uae09", "\ud63cOPEN", "\uc81cOPEN", "1\ub4f1\uae09"]
)
def test_exact_header_cells(distance, grade):
    actual = conditions.parse_conditions(header(grade, distance), "20260712_1_1")
    assert actual["status"] == "observed"
    assert actual["distance_m"] == int(distance[:-1])
    assert actual["class_text"] == grade
    assert actual["cells"]["distance"] == [0, 1, 1]


@pytest.mark.parametrize(
    "html",
    [
        "<table><tr><td>template</td></tr></table>",
        header() + header(),
        header(distance="M"),
        header(grade="Grade2"),
        header(distance="1200M 1"),
        header().replace("<td>1200M", "<td colspan='2'>1200M"),
        header().replace("</table>", ""),
        header().replace("<td>x</td>", "", 1),
    ],
)
def test_ambiguous_or_malformed_header_is_unknown(html):
    assert conditions.parse_conditions(html, "20260712_1_1")["status"] == "unknown"


@pytest.mark.parametrize("expected", ["20260713_1_1", "20260712_2_1", "20260712_1_2"])
def test_expected_identity_is_not_inferred_from_request(expected):
    assert (
        conditions.parse_conditions(header(), expected)["reason"]
        == "body_identity_mismatch"
    )


def test_physical_venue_and_grade_not_finish_rank():
    actual = conditions.parse_conditions(
        header("\ud63cOPEN", "1800M", "\uc601\ucc9c"), "20260712_4_1"
    )
    assert actual["meet"] == 4
    assert actual["class_text"] == "\ud63cOPEN"
    assert (
        conditions.parse_conditions(header("1"), "20260712_1_1")["status"] == "unknown"
    )


def context(meet=1, distance=1200, grade="classA"):
    return {
        "status": "observed",
        "meet": meet,
        "distance_m": distance,
        "class_text": grade,
    }


@pytest.mark.parametrize(
    "delta,allowed", [(200, True), (-200, True), (201, False), (-201, False)]
)
def test_distance_boundary(delta, allowed):
    assert (
        research.eligible(context(), context(distance=1200 + delta), "distance90")
        is allowed
    )


def test_exact_class_same_venue_and_unknown():
    assert not research.eligible(context(), context(grade="classB"), "class90")
    assert not research.eligible(context(), context(meet=2), "distance90")
    assert not research.eligible(context(), {}, "venue90")
    assert research.eligible(context(), context(distance=1600), "class90")
    with pytest.raises(ValueError, match="unknown_arm"):
        research.eligible({}, {}, "typo")


def fixture():
    targets = {
        "20260712_1_1": [{"horse_id": str(n), "chul_no": n} for n in range(1, 6)]
    }
    history = [
        {
            "race_id": "20260601_1_1",
            "horse_id": str(n),
            "rank": 6 - n,
            "observed_roster_size": 5,
            "tier": "html_only",
        }
        for n in range(1, 6)
    ]
    ctx = {"20260712_1_1": context(), "20260601_1_1": context()}
    return targets, history, ctx


def test_baseline_reproduces_original_and_matching_arms():
    targets, history, ctx = fixture()
    old = form.predict(targets, history)["ledger"][0]["arms"]["expanded90"]
    actual = research.predict(targets, history, ctx)["ledger"][0]["arms"]
    for arm in research.ARMS:
        assert actual[arm]["horse_ids"] == old["horse_ids"]
        assert [r["score_fraction"] for r in actual[arm]["rows"]] == [
            r["score_fraction"] for r in old["rows"]
        ]
        assert all(r["fallback"] is None for r in actual[arm]["rows"])


@pytest.mark.parametrize("missing", ["20260712_1_1", "20260601_1_1"])
def test_missing_conditions_fallback_without_skipping(missing):
    targets, history, ctx = fixture()
    del ctx[missing]
    actual = research.predict(targets, history, ctx)
    arms = actual["ledger"][0]["arms"]
    for arm in research.ARMS[1:]:
        assert arms[arm]["horse_ids"] == arms["expanded90"]["horse_ids"]
        assert all(r["fallback"] for r in arms[arm]["rows"])
        assert actual["diagnostics"][arm]["fallback_rows"] == 5


def test_fallback_is_per_horse_not_entire_race():
    targets, history, ctx = fixture()
    ctx["20260601_1_1"] = context(distance=1800)
    ctx["20260602_1_1"] = context()
    history.append({**history[0], "race_id": "20260602_1_1", "rank": 1})
    rows = research.predict(targets, history, ctx)["ledger"][0]["arms"]["distance90"][
        "rows"
    ]
    assert rows[0]["fallback"] is None
    assert rows[0]["prior_ids"] == ["20260602_1_1"]
    assert all(r["fallback"] == "no_eligible_prior" for r in rows[1:])


def test_strict_dates_and_inclusive_lower_boundary():
    targets, history, ctx = fixture()
    for day in ("20260412", "20260413", "20260712", "20260713"):
        history.append({**history[0], "race_id": day + "_1_1"})
        ctx[day + "_1_1"] = context()
    row = research.predict(targets, history, ctx)["ledger"][0]["arms"]["joint90"][
        "rows"
    ][0]
    assert row["prior_ids"] == ["20260413_1_1", "20260601_1_1"]


def test_empty_history_ties_and_identity_only_boundary():
    targets, _, ctx = fixture()
    result = research.predict(targets, [], ctx)
    for arm in research.ARMS:
        selected = result["ledger"][0]["arms"][arm]
        assert selected["horse_ids"] == ["1", "2", "3"]
        assert selected["boundary_score_tie"]
        assert all(
            Fraction(r["score_fraction"]) == Fraction(1, 2) for r in selected["rows"]
        )
    targets["20260712_1_1"][0]["rank"] = 1
    with pytest.raises(ValueError, match="identity_only"):
        research.predict(targets, [], ctx)


def test_input_order_and_target_result_fields_do_not_change_selections():
    targets, history, ctx = fixture()
    expected = research.predict(targets, history, ctx)
    ctx["20260712_1_1"].update(rank=99, odds=0, outcome_status="void")
    targets["20260712_1_1"].reverse()
    assert research.predict(targets, list(reversed(history)), ctx) == expected


def test_duplicate_roster_and_history_rejected():
    targets, history, ctx = fixture()
    with pytest.raises(ValueError, match="duplicate_history"):
        research.predict(targets, history + history[:1], ctx)
    targets["20260712_1_1"].append(targets["20260712_1_1"][0])
    with pytest.raises(ValueError, match="duplicate_roster"):
        research.predict(targets, history, ctx)


@pytest.mark.parametrize(
    "status,expected",
    [
        ("unique_top3_observed", "match"),
        ("source_conflict", "pending"),
        ("void_reported_no_top3", "undefined"),
    ],
)
def test_full_population_states_and_no_success_rate(status, expected):
    targets, history, ctx = fixture()
    predictions = research.predict(targets, history, ctx)
    before = deepcopy(predictions)
    outcomes = {"20260712_1_1": {"status": status, "horse_ids": ["3", "4", "5"]}}
    report = research.evaluate(predictions, outcomes)
    assert predictions == before
    for arm in research.ARMS:
        assert report["totals"]["all"][arm] == {"races": 1, expected: 1}
    with pytest.raises(ValueError, match="population_mismatch"):
        research.evaluate(predictions, {})


def test_execution_failure_and_invalid_answers():
    targets, _, ctx = fixture()
    targets["20260712_1_1"] = targets["20260712_1_1"][:2]
    predictions = research.predict(targets, [], ctx)
    outcome = {"20260712_1_1": {"status": "source_conflict", "horse_ids": None}}
    assert (
        research.evaluate(predictions, outcome)["totals"]["all"]["joint90"][
            "execution_failure"
        ]
        == 1
    )
    outcome["20260712_1_1"] = {
        "status": "unique_top3_observed",
        "horse_ids": ["1", "1", "2"],
    }
    with pytest.raises(ValueError, match="invalid_unique"):
        research.evaluate(predictions, outcome)


def test_capture_pin_and_encoding_fail_closed(tmp_path):
    raw = header().encode("euc-kr")
    path = tmp_path / "raw.html"
    path.write_bytes(raw)
    capture = {
        "status": "captured",
        "raw": {"path": "raw.html", "sha256": digest(raw)},
        "encoding": "euc-kr",
        "completed_at": "2026-10-13T00:00:00+00:00",
    }
    assert (
        conditions.from_capture(tmp_path, "20260712_1_1", capture, {})["status"]
        == "observed"
    )
    capture["encoding"] = "utf-8"
    assert (
        conditions.from_capture(tmp_path, "20260712_1_1", capture, {})["status"]
        == "unknown"
    )
    path.write_bytes(raw + b"changed")
    with pytest.raises(ValueError):
        conditions.from_capture(tmp_path, "20260712_1_1", capture, {})


def test_run_pins_input_and_predictions_before_evaluation(tmp_path, monkeypatch):
    targets, history, ctx = fixture()
    source = tmp_path / "source.json"
    source_sha = save(source, {"test_fixture": True})
    plan = tmp_path / "plan.json"
    plan_sha = save(
        plan,
        {
            "format_version": "condition-form-exploration-plan-v1",
            "source_plan": str(source),
            "source_plan_sha256": source_sha,
            **research.RECIPE,
            "training_approved": False,
            "counts_as_70_percent_evidence": False,
        },
    )
    outcome = {"20260712_1_1": {"status": "source_conflict", "horse_ids": None}}
    monkeypatch.setattr(form, "load_sources", lambda _: (targets, outcome, history))
    monkeypatch.setattr(conditions, "load_conditions", lambda _: ctx)
    output = tmp_path / "run"
    original = research.evaluate

    def evaluate_after_save(predictions, outcomes):
        assert (output / "predictions.json").exists()
        assert not (output / "report.json").exists()
        return original(predictions, outcomes)

    monkeypatch.setattr(research, "evaluate", evaluate_after_save)
    result = research.run(plan, plan_sha, output)
    assert result["target_manifest_sha256"] == digest(
        (output / "targets.json").read_bytes()
    )
    report = json.loads((output / "report.json").read_text())
    assert report["fit_count"] == 0
    assert report["counts_as_70_percent_evidence"] is False
    assert report["prediction_success_rate"] is None
    with pytest.raises(FileExistsError):
        research.run(plan, plan_sha, output)
    source.write_text("{}")
    with pytest.raises(ValueError):
        research.run(plan, plan_sha, tmp_path / "other")


def test_protocol_rejects_recipe_change(tmp_path):
    plan = tmp_path / "plan.json"
    sha = save(
        plan,
        {
            "format_version": "condition-form-exploration-plan-v1",
            **research.RECIPE,
            "distance_tolerance_metres": 201,
        },
    )
    with pytest.raises(ValueError, match="unrecognized_protocol"):
        research.run(plan, sha, tmp_path / "run")


def test_prior_partition_and_non_monotonic_direct_fallback():
    targets, history, ctx = fixture()
    ctx["20260601_1_1"] = context(grade="classB")
    extra = {**history[0], "race_id": "20260602_2_1", "rank": 1}
    history.append(extra)
    ctx[extra["race_id"]] = context(meet=2)
    output = research.predict(targets, history, ctx)
    arms = output["ledger"][0]["arms"]
    assert Fraction(arms["venue90"]["rows"][0]["score_fraction"]) == Fraction(1, 3)
    assert Fraction(arms["class90"]["rows"][0]["score_fraction"]) == Fraction(1, 2)
    assert arms["class90"]["rows"][0]["fallback"] == "no_eligible_prior"
    assert arms["class90"]["rows"][0]["prior_partition"] == {"conditions_mismatch": 2}
    assert output["diagnostics"]["class90"]["race_path_all_fallback"] == 1
    for arm in arms.values():
        for row in arm["rows"]:
            assert sum(row["prior_partition"].values()) == row["baseline_prior_count"]


def test_condition_parser_does_not_depend_on_result_table():
    a = header()
    b = a + "<table><caption>results</caption><tr><td>1</td><td>99.9</td></tr></table>"
    assert conditions.parse_conditions(
        a, "20260712_1_1"
    ) == conditions.parse_conditions(b, "20260712_1_1")


@pytest.mark.parametrize("a,b,expected", [(1110, 1300, True), (1610, 1400, False)])
def test_distance_not_rounded(a, b, expected):
    assert (
        research.eligible(context(distance=a), context(distance=b), "distance90")
        is expected
    )

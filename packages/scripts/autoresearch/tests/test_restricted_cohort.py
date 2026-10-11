"""Restricted source/label boundary tests; fixtures never confer real approval."""

import asyncio
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import kra_race_card_pdf_bundle as bundle
from autoresearch import restricted_cohort as c
from autoresearch.tests.race_card_pdf_capture_fixture import capture_chain, entry
from autoresearch.tests.test_kra_race_card_pdf_bundle import plan_for
from autoresearch.tests.test_prerace_hash_witness import inputs


def raw_features():
    return {
        "age": 3,
        "wgBudam": 55.5,
        "rating": 10,
        "rcCntT": 5,
        "ord1CntT": 1,
        "ord2CntT": 1,
        "ord3CntT": 1,
    }


def pdf_features():
    return {
        **dict.fromkeys(c.NUMERIC_FIELDS),
        **{f"{k}_missing": True for k in c.NUMERIC_FIELDS},
        "training_summary_truncated": False,
    }


def corpus_fixture():
    sources, results = [], []
    for day in ("20261010", "20261011"):
        key = f"{day}_1_1"
        roster, features = [], []
        for gate in range(1, 5):
            runner = {
                "chul_no": gate,
                "horse_id": str(gate),
                "raw_horse_id": f"00{gate}",
            }
            roster.append(runner)
            raw = {**raw_features(), "age": gate + 1}
            features.append(
                {**runner, "features": c.project_features(raw, pdf_features())}
            )
            results.append(
                {
                    "race_id": key,
                    "chul_no": gate,
                    "horse_id": str(gate),
                    "raw_horse_id": f"00{gate}",
                    "raw_ord": gate,
                    "raw_rc_time": 60 + gate,
                    "raw_ord_bigo": "",
                    "evidence": "ranked_finish_observed",
                }
            )
        sources.append(
            {
                "race_id": key,
                "source_eligible": True,
                "source_reasons": [],
                "roster": roster,
                "feature_rows": features,
                "expected_roster_count": 4,
            }
        )
    return {
        "format_version": "kra-restricted-corpus-v1",
        "feature_contract": c.CONTRACT,
        "selection_policy": c.POLICY,
        "counts_as_70_percent_evidence": False,
        "ledger": c.join_labels(sources, results),
    }


def test_labels_do_not_affect_source_projection():
    raw, pdf = raw_features(), pdf_features()
    original = c.project_features(raw, pdf)
    raw.update(ord=1, rcTime=99, winOdds=1.1, ilsu=999, result="changed")
    assert c.project_features(raw, pdf) == original
    assert original["training_minutes"] is None
    assert original["training_minutes_missing"] is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("age", True),
        ("age", 0),
        ("age", 2.5),
        ("rating", -1),
        ("wgBudam", float("inf")),
        ("rcCntT", "unknown"),
    ],
)
def test_invalid_source_numeric_rejected(field, value):
    raw = raw_features()
    raw[field] = value
    with pytest.raises(ValueError):
        c.project_features(raw, pdf_features())


def test_missing_flag_units_and_career_consistency():
    pdf = pdf_features()
    pdf.update(trainer_win_rate=9.6, trainer_win_rate_missing=False)
    with pytest.raises(ValueError, match="fraction"):
        c.project_features(raw_features(), pdf)
    pdf["trainer_win_rate"] = 0.096
    assert c.project_features(raw_features(), pdf)["trainer_win_rate"] == 0.096
    pdf["trainer_win_rate_missing"] = True
    with pytest.raises(ValueError, match="flag"):
        c.project_features(raw_features(), pdf)
    with pytest.raises(ValueError, match="exceed"):
        c.project_features({**raw_features(), "rcCntT": 2}, pdf_features())
    raw = raw_features()
    del raw["rating"]
    with pytest.raises(ValueError, match="keys"):
        c.project_features(raw, pdf_features())


@pytest.mark.parametrize(
    "value", [True, 0, "000", "1.0", " 1", "1e2", "\uff11\uff12", 1.5]
)
def test_rejects_ambiguous_horse_ids(value):
    with pytest.raises(ValueError):
        c.horse_id(value)


def test_exact_leading_zero_identity_and_complete_rosters():
    corpus = corpus_fixture()
    assert len(c.validate_corpus(corpus)) == 2
    assert c.horse_id("0056123") == "56123"
    source = corpus["ledger"][0]
    results = copy.deepcopy(source["results"])
    results[0]["horse_id"] = "99"
    result = c.join_labels([source], results)[0]
    assert not result["training_selected"]
    assert "full_result_roster_identity_mismatch" in result["label_reasons"]
    assert result["feature_rows"] == source["feature_rows"]


def test_blocked_and_void_races_stay_in_inventory():
    corpus = corpus_fixture()
    sources = corpus["ledger"]
    sources[0]["source_eligible"] = False
    sources[0]["source_reasons"] = ["known_name_mismatch"]
    results = copy.deepcopy(sources[1]["results"])
    for row in results:
        row.update(raw_ord=0, raw_rc_time=0, evidence="unresolved")
    joined = c.join_labels(sources, sources[0]["results"] + results)
    assert len(joined) == 2
    assert not any(r["training_selected"] for r in joined)
    assert joined[1]["label_top3"] is None


@pytest.mark.parametrize(
    "change", ["label", "runner", "selection", "numeric", "duplicate"]
)
def test_corpus_integrity(change):
    corpus = corpus_fixture()
    race = corpus["ledger"][0]
    if change == "label":
        race["label_top3"] = ["1", "2", "4"]
    elif change == "runner":
        race["feature_rows"].pop()
    elif change == "selection":
        race["training_selected"] = False
    elif change == "numeric":
        race["feature_rows"][0]["features"]["age_missing"] = True
    else:
        corpus["ledger"].append(copy.deepcopy(race))
    with pytest.raises(ValueError):
        c.validate_corpus(corpus)


def test_actual_synthetic_raw_replay_then_feature_projection(tmp_path):
    pytest.importorskip("pdfplumber")
    chain = asyncio.run(
        capture_chain(tmp_path, rows=[{**entry(n), **raw_features()} for n in (1, 2)])
    )
    plan = plan_for(chain)
    archive = bundle.build_bundle(plan, archive_root=tmp_path)
    arguments = inputs(plan, archive, tmp_path)
    audit = c.audit_archive(**arguments)
    rows = c.source_rows(plan, archive, audit, tmp_path)
    assert len(rows) == 1 and rows[0]["source_eligible"]
    assert [r["horse_id"] for r in rows[0]["feature_rows"]] == ["1", "2"]
    assert rows[0]["feature_rows"][0]["features"]["wgBudam"] == 55.5
    page = Path(audit["ledger"][0]["evidence"]["entry"]["pages"][0]["path"])
    page.write_bytes(page.read_bytes() + b" ")
    with pytest.raises(ValueError):
        c.source_rows(plan, archive, audit, tmp_path)

"""Retrospective, pinned official race-header conditions; not pre-race inputs."""

from __future__ import annotations

import re
from pathlib import Path

from shared.kra_race_identity import MEET_NAMES, validate_race_identity
from shared.official_result_support import HEADER, tables

from autoresearch import official_history_catalog as catalog
from autoresearch.frozen_history_view import replay_frozen
from autoresearch.observed_history_seed import pinned_path
from autoresearch.official_history_support import replay_archive

CLASS = re.compile(
    r"(?:[\uad6d\ud63c\uc81c]?[1-6]\ub4f1\uae09|[\uad6d\ud63c\uc81c]OPEN)"
)
DISTANCE = re.compile(r"([0-9]{3,4})M")


def parse_conditions(html, expected):
    result = {"race_id": expected, "status": "unknown", "reason": None}
    items = tables(html)
    headers = [
        (ti, ri, ci, match)
        for ti, table in enumerate(items)
        for ri, row in enumerate(table.rows)
        for ci, cell in enumerate(row)
        if (match := HEADER.fullmatch(cell.text))
    ]
    if len(headers) != 1:
        return {**result, "reason": "missing_or_ambiguous_dated_header"}
    ti, ri, ci, match = headers[0]
    year, month, day, number, venue = match.groups()
    meet = MEET_NAMES.get(venue)
    if meet is None:
        return {**result, "reason": "unknown_physical_venue"}
    date, number = year + month + day, int(number)
    validate_race_identity(meet, date, number)
    body_id = f"{date}_{meet}_{number}"
    if body_id != expected:
        return {**result, "reason": "body_identity_mismatch", "body_race_id": body_id}
    table = items[ti]
    if (
        not table.closed
        or table.invalid
        or ci != 0
        or len(table.rows[ri]) != 6
        or ri + 1 >= len(table.rows)
        or len(table.rows[ri + 1]) != 7
    ):
        return {**result, "reason": "unrecognized_header_structure"}
    grade, distance = table.rows[ri + 1][:2]
    parsed_distance = DISTANCE.fullmatch(distance.text)
    if (
        grade.span
        or distance.span
        or grade.tag != "td"
        or distance.tag != "td"
        or not CLASS.fullmatch(grade.text)
        or not parsed_distance
        or not 500 <= int(parsed_distance[1]) <= 5000
    ):
        return {**result, "reason": "invalid_condition_cells"}
    return {
        **result,
        "status": "observed",
        "meet": meet,
        "distance_m": int(parsed_distance[1]),
        "class_text": grade.text,
        "body_race_id": body_id,
        "cells": {
            "header": [ti, ri, ci],
            "class": [ti, ri + 1, 0],
            "distance": [ti, ri + 1, 1],
        },
        "raw_class_text": grade.text,
        "raw_distance_text": distance.text,
    }


def from_capture(directory, identity, capture, provenance):
    common = {
        "provenance": provenance,
        "source_tier": "official_html_header_only",
        "historical_pre_race_availability_verified": False,
    }
    if capture["status"] != "captured":
        return {
            "race_id": identity,
            "status": "unknown",
            "reason": "fetch_error",
            **common,
        }
    raw = pinned_path(directory, capture["raw"]).read_bytes()
    try:
        parsed = parse_conditions(
            raw.decode(capture["encoding"], errors="strict"), identity
        )
    except (UnicodeError, LookupError, ValueError) as exc:
        parsed = {
            "race_id": identity,
            "status": "unknown",
            "reason": f"parse_error:{exc}",
        }
    return {
        **parsed,
        **common,
        "raw": capture["raw"],
        "encoding": capture["encoding"],
        "captured_at": capture["completed_at"],
    }


def load_conditions(plan):
    output = {}
    for label in ("target", "earlier"):
        spec = plan[label]
        seed = replay_frozen(
            Path(spec["root"]), Path(spec["seed"]), spec["seed_sha256"]
        )
        directory = Path(spec["archive"])
        evidence = replay_archive(
            directory, spec["archive_sha256"], seed, spec["seed_sha256"]
        )
        for identity in sorted({r["race_id"] for r in seed["records"]}):
            if identity in output:
                raise ValueError("conditions_source_overlap")
            item = evidence[identity]
            output[identity] = from_capture(
                directory,
                identity,
                item["capture"],
                {"source": label, **spec, "receipt": item["receipt"]},
            )
    spec = plan["catalog"]
    directory = Path(spec["directory"])
    replayed = catalog.replay(
        directory, spec["index_sha256"], spec["archive_sha256"], Path(spec["discovery"])
    )
    for group in replayed["groups"]:
        identity = group["race_id"]
        if identity in output:
            raise ValueError("conditions_source_overlap")
        capture = catalog.parse_json(
            pinned_path(directory / "details", group["receipt"]).read_bytes()
        )
        output[identity] = from_capture(
            directory / "details",
            identity,
            capture,
            {
                "source": "catalog",
                **spec,
                "receipt": group["receipt"],
                "listing": group["listing"],
            },
        )
    return output

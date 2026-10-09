"""Bounded extraction of current-horse panels from official KRA race cards."""

from __future__ import annotations

import io
import re
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Any

PARSER_VERSION = "kra-race-card-pdf-v1"
SOURCE_ID = "kra_official_race_card_pdf"
MAX_PDF_BYTES = 20 * 1024 * 1024
MEETINGS = {
    1: ("seoul", "s", "\uc11c\uc6b8"),
    2: ("jeju", "j", "\uc81c\uc8fc"),
    3: ("busan", "b", "\ubd80\uacbd"),
}
NUMERIC_FIELDS = (
    "training_count",
    "training_minutes",
    "training_window_days",
    "training_gu_count",
    "training_seup_count",
    "swimming_count",
    "swimming_laps",
    "trainer_wins",
    "trainer_win_rate",
)

# These labels are confined to the second current-horse column, never history.
TRAINING = re.compile(
    r"^(?:(\d+)\uc8fc\uc870\uad50\s*:\s*)?"
    r"(\d+)\ud68c\s*(\d+)\ubd84\(([^)]*)\)"
    r"(?:\s*/\s*\uad6c(\d+)\uc2b5(\d+))?$"
)
TRUNCATED_TRAINING = re.compile(
    r"^(?:(\d+)\uc8fc\uc870\uad50\s*:\s*)?"
    r"(\d+)\ud68c\s*(\d+)\ubd84\([^)]*$"
)
SWIMMING = re.compile(r"^\uc218\uc601\s*:\s*(\d+)\ud68c\s*(\d+)\ubc14\ud034$")
GATE = re.compile(r"^\ucd9c\ubc1c\uc870\uad50\s*:\s*(\d{6})\(([^,]*),([^)]*)\)$")
TRAINER = re.compile(r"^\((\d+)\uc870\)(.+?)\s+(\d[\d,]*)\uc2b9\((\d+(?:\.\d+)?)%\)$")
JEJU_TRAINER = re.compile(r"^\uc870\uad50\uc0ac\s*:\s*(.+?)\((\d+)\uc870\)$")
TREATMENT = re.compile(r"^(\d{6})([^\d].*?)(?:(\d+)\ud68c)?$")
HISTORY = re.compile(r"[\u2460-\u2473]|^\d{6}(?:[- ]\d+R|[\uc11c\ubd80]\d+R)")
FOOTER = re.compile(
    r"(\uc11c\uc6b8|\uc81c\uc8fc|\ubd80\uacbd)\s*(\d+)\uacbd\uc8fc"
    r"\s*[\[\u3014(](\d{4})\.(\d{2})\.(\d{2})[\]\u3015)]"
)


def validate_identity(meet: int, race_date: str, race_no: int) -> None:
    if type(meet) is not int or meet not in MEETINGS:
        raise ValueError("meet must be 1 (Seoul), 2 (Jeju), or 3 (Busan)")
    if type(race_no) is not int or not 1 <= race_no <= 20:
        raise ValueError("race_no must be an integer between 1 and 20")
    if not isinstance(race_date, str) or not re.fullmatch(r"20\d{6}", race_date):
        raise ValueError("race_date must be YYYYMMDD within 2000-2099")
    datetime.strptime(race_date, "%Y%m%d")


def race_card_url(meet: int, race_date: str, race_no: int) -> str:
    validate_identity(meet, race_date, race_no)
    directory, prefix, _ = MEETINGS[meet]
    return (
        f"https://race.kra.co.kr/down/pdf/{directory}/chulma/"
        f"{prefix}_run_hr_{race_date[2:]}_{race_no:02d}.pdf"
    )


def normalize_horse_name(value: str) -> str:
    return "".join(unicodedata.normalize("NFKC", value).split())


def _event_date(value: str, race_date: str, issues: list[str]) -> str | None:
    try:
        parsed = datetime.strptime("20" + value, "%Y%m%d").strftime("%Y%m%d")
    except ValueError:
        issues.append("invalid_event_date")
        return None
    if parsed > race_date:
        issues.append("event_after_race_date")
    return parsed


def parse_horse_panel(
    *, chul_no: int, horse_name: str, text: str, race_date: str
) -> dict[str, Any]:
    """Parse one already isolated panel; unprinted numbers stay null."""
    row: dict[str, Any] = {
        "chulNo": chul_no,
        "hrName": normalize_horse_name(horse_name),
        "hrNo": None,
        **dict.fromkeys(NUMERIC_FIELDS),
        "trainer_name": None,
        "training_riders": None,
        "training_summary_truncated": False,
        "gate_training_date": None,
        "gate_training_rider": None,
        "gate_training_status": None,
        "recent_listed_treatments": [],
        "evidence_lines": {},
        "issues": [],
    }
    issues = row["issues"]
    if not row["hrName"] or not 1 <= chul_no <= 20:
        issues.append("invalid_horse_identity")
    seen: Counter[str] = Counter()
    for raw in text.splitlines():
        line = " ".join(unicodedata.normalize("NFKC", raw).split())
        if HISTORY.search(raw) or HISTORY.search(line):
            issues.append("history_in_current_panel")
            continue
        match = TRAINING.fullmatch(line)
        if match:
            weeks, count, minutes, riders, gu, seup = match.groups()
            row.update(
                training_count=int(count),
                training_minutes=int(minutes),
                training_window_days=int(weeks) * 7 if weeks else None,
                training_riders=[
                    v.strip() for v in re.split(r"[,/]", riders) if v.strip()
                ],
                training_gu_count=int(gu) if gu is not None else None,
                training_seup_count=int(seup) if seup is not None else None,
            )
            field = "training"
        elif match := TRUNCATED_TRAINING.fullmatch(line):
            weeks, count, minutes = match.groups()
            row.update(
                training_count=int(count),
                training_minutes=int(minutes),
                training_window_days=int(weeks) * 7 if weeks else None,
                training_summary_truncated=True,
            )
            field = "training"
        elif match := SWIMMING.fullmatch(line):
            row.update(swimming_count=int(match[1]), swimming_laps=int(match[2]))
            field = "swimming"
        elif match := GATE.fullmatch(line):
            row.update(
                gate_training_date=_event_date(match[1], race_date, issues),
                gate_training_rider=match[2].strip() or None,
                gate_training_status=match[3].strip() or None,
            )
            field = "gate"
        elif match := TRAINER.fullmatch(line):
            row.update(
                trainer_name=match[2],
                trainer_wins=int(match[3].replace(",", "")),
                trainer_win_rate=float(match[4]) / 100,
            )
            field = "trainer"
        elif match := JEJU_TRAINER.fullmatch(line):
            row["trainer_name"] = match[1]
            field = "trainer"
        elif match := TREATMENT.fullmatch(line):
            date = _event_date(match[1], race_date, issues)
            row["recent_listed_treatments"].append(
                {
                    "date": date,
                    "description": match[2].strip(),
                    "printed_count": int(match[3]) if match[3] else None,
                    "evidence": line,
                }
            )
            continue
        else:
            continue
        seen[field] += 1
        row["evidence_lines"][field] = line
    issues.extend(f"ambiguous_{key}" for key, count in seen.items() if count > 1)
    if not seen:
        issues.append("unsupported_current_panel")
    row["missing_numeric_fields"] = [key for key in NUMERIC_FIELDS if row[key] is None]
    row["issues"] = sorted(set(issues))
    return row


def _panel_boxes(page: Any, anchor: dict[str, Any], meet: int) -> tuple[tuple, tuple]:
    left, name_right, panel_right = (
        (11.0, 113.0, 199.0) if meet == 2 else (10.0, 110.0, 196.0)
    )
    rules = [
        rect
        for rect in page.rects
        if rect["x0"] < left + 1
        and rect["x1"] > left + 11
        and 0 <= rect["bottom"] - rect["top"] < 0.7
    ]
    tops = [r["top"] for r in rules if 0 <= anchor["top"] - r["top"] <= 8]
    bottoms = [
        r["top"]
        for r in rules
        if r["x1"] - r["x0"] > 80 and r["top"] > anchor["bottom"] + 20
    ]
    if not tops or not bottoms:
        raise ValueError("unsupported_row_boundaries")
    top, bottom = max(tops), min(bottoms)
    if not 75 <= bottom - top <= 125:
        raise ValueError("unsupported_row_height")
    # Confirm both separators in this row before using the template coordinates.
    for x in (name_right, panel_right):
        if not any(
            abs(r["x0"] - x) < 0.6
            and r["x1"] - r["x0"] < 0.7
            and r["top"] < anchor["bottom"]
            and r["bottom"] > anchor["top"]
            for r in page.rects
        ):
            raise ValueError("unsupported_column_boundaries")
    return (
        (left + 1, anchor["top"] - 0.5, name_right - 0.5, anchor["bottom"] + 0.5),
        (name_right + 0.5, top + 0.7, panel_right - 0.5, bottom - 0.5),
    )


def parse_race_card_pdf(
    content: bytes, *, meet: int, race_date: str, race_no: int
) -> dict[str, Any]:
    """Reject unknown layouts/identities, retaining evidence for known panels."""
    validate_identity(meet, race_date, race_no)
    if not content.startswith(b"%PDF-") or len(content) > MAX_PDF_BYTES:
        raise ValueError("invalid_pdf_bytes")
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("Install the kra-scripts race-card-pdf extra") from exc

    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    identities = []
    scheduled_start = None
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        if not 1 <= len(pdf.pages) <= 8:
            raise ValueError("unsupported_page_count")
        for page in pdf.pages:
            if abs(page.width - 595) > 1 or abs(page.height - 842) > 1:
                raise ValueError("unsupported_page_size")
            if len(page.chars) > 100_000:
                raise ValueError("excessive_page_characters")
            footer = (
                page.crop(
                    (0, page.height - 100, page.width, page.height)
                ).extract_text()
                or ""
            )
            matches = FOOTER.findall(footer)
            expected = (
                MEETINGS[meet][2],
                str(race_no),
                race_date[:4],
                race_date[4:6],
                race_date[6:],
            )
            identities.append(
                {
                    "page": page.page_number,
                    "footer": footer,
                    "matches_requested": matches == [expected],
                }
            )
        if not all(item["matches_requested"] for item in identities):
            issues.append("document_identity_mismatch_or_missing")
        else:
            header = (
                pdf.pages[0].crop((0, 0, pdf.pages[0].width, 150)).extract_text() or ""
            )
            starts = re.findall(r"(\d{1,2})\uc2dc(\d{2})\ubd84", header)
            if starts:
                hour, minute = starts[0]
                if int(hour) <= 23 and int(minute) <= 59:
                    scheduled_start = f"{int(hour):02d}{minute}"
            for page in pdf.pages:
                anchors = [
                    word
                    for word in page.crop((9, 0, 25.5, page.height)).extract_words()
                    if 10 <= word["x0"] <= 25
                    and re.fullmatch(r"\d{1,2}", word["text"])
                    and word["bottom"] - word["top"] >= 10
                ]
                for anchor in sorted(anchors, key=lambda value: value["top"]):
                    try:
                        name_box, panel_box = _panel_boxes(page, anchor, meet)
                        name = (
                            page.crop(name_box).extract_text(
                                x_tolerance=1, y_tolerance=2
                            )
                            or ""
                        )
                        prefix = re.match(r"^(\d{1,2})\s*(\D.*)$", name.strip())
                        if not prefix or prefix[1] != anchor["text"]:
                            raise ValueError("horse_header_mismatch")
                        text = (
                            page.crop(panel_box).extract_text(
                                x_tolerance=1, y_tolerance=2
                            )
                            or ""
                        )
                        row = parse_horse_panel(
                            chul_no=int(prefix[1]),
                            horse_name=prefix[2],
                            text=text,
                            race_date=race_date,
                        )
                        row.update(
                            page=page.page_number,
                            name_bbox=list(name_box),
                            panel_bbox=list(panel_box),
                        )
                        rows.append(row)
                    except ValueError as exc:
                        issues.append(
                            f"page_{page.page_number}_runner_{anchor['text']}:{exc}"
                        )
                if not anchors:
                    issues.append(f"page_{page.page_number}:no_current_horse_headers")
    numbers = [row["chulNo"] for row in rows]
    if not rows:
        issues.append("no_parsed_horses")
    if len(numbers) != len(set(numbers)):
        issues.append("duplicate_runner_numbers")
    if any(row["issues"] for row in rows):
        issues.append("horse_panel_issues")
    return {
        "parser_version": PARSER_VERSION,
        "source_id": SOURCE_ID,
        "meet": meet,
        "race_date": race_date,
        "race_no": race_no,
        "race_id": f"{race_date}_{meet}_{race_no}",
        "parser_status": "parsed" if not issues else "blocked",
        "issues": sorted(set(issues)),
        "document_identity": identities,
        "scheduled_start_time_from_pdf": scheduled_start,
        "horse_count": len(rows),
        "rows": rows,
        "numeric_field_coverage": {
            key: sum(row[key] is not None for row in rows) for key in NUMERIC_FIELDS
        },
        "treatment_history_is_exhaustive": False,
        "current_race_results_extracted": False,
    }

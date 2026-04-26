from pathlib import Path

from infrastructure.prerace_sources.base import RawSourceResponse
from infrastructure.prerace_sources.changes import ENTRY_CHANGE_BULLETIN_SPEC
from scripts.capture_entry_change_bulletin import (
    SNAPSHOT_SCHEMA_VERSION,
    build_snapshot_paths,
    write_entry_change_snapshot,
)


def _response(html: str) -> RawSourceResponse:
    body = html.encode("euc-kr")
    return RawSourceResponse(
        spec=ENTRY_CHANGE_BULLETIN_SPEC,
        requested_url="https://race.kra.co.kr/raceFastreport/ChulmapyoChange.do?meet=1",
        status_code=200,
        headers={"content-type": "text/html"},
        body=body,
        fetched_at="2026-04-26T01:00:00+00:00",
        encoding="euc-kr",
    )


def test_build_snapshot_paths_uses_meet_and_fetch_timestamp(tmp_path: Path) -> None:
    paths = build_snapshot_paths(
        output_dir=tmp_path,
        meet=1,
        fetched_at="2026-04-26T01:00:00+00:00",
    )

    assert paths.raw_html_path.name == "meet1_20260426T010000p0000.html"
    assert paths.manifest_path.name == "meet1_20260426T010000p0000.json"


def test_write_entry_change_snapshot_persists_raw_html_and_parsed_manifest(
    tmp_path: Path,
) -> None:
    html = """
    <h2><img alt="기수변경" /></h2>
    <table><tbody>
      <tr>
        <td>2026/04/26</td>
        <td>4</td>
        <td>7</td>
        <td><a href="javascript:goHorse('0055001','1')">테스트말</a></td>
        <td><a href="javascript:goJockey('080111','1')">기수전</a></td>
        <td>55.0</td>
        <td><a href="javascript:goJockey('080222','1')">기수후</a></td>
        <td>55.0</td>
        <td>부상</td>
        <td>04/26 11:05</td>
      </tr>
    </tbody></table>
    """

    summary = write_entry_change_snapshot(
        response=_response(html),
        meet=1,
        output_dir=tmp_path,
    )

    raw_path = Path(str(summary["raw_html_path"]))
    manifest_path = Path(str(summary["manifest_path"]))
    assert raw_path.exists()
    assert manifest_path.exists()

    manifest = manifest_path.read_text(encoding="utf-8")
    assert SNAPSHOT_SCHEMA_VERSION in manifest
    assert '"source_snapshot_at": "2026-04-26T01:00:00+00:00"' in manifest
    assert '"notice_count": 1' in manifest
    assert '"change_type": "jockey_change"' in manifest
    assert '"source_snapshot_at": "2026-04-26T01:00:00+00:00"' in manifest

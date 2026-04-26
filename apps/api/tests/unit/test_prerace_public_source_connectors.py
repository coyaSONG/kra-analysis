import httpx
import pytest

from infrastructure.prerace_sources.base import (
    PublicSourceFetchError,
    infer_response_encoding,
)
from infrastructure.prerace_sources.changes import (
    EntryChangeConnector,
    parse_entry_change_bulletin_html,
)
from infrastructure.prerace_sources.entry import (
    EntryMeetingListConnector,
    EntryRaceCardConnector,
)
from infrastructure.prerace_sources.profiles import (
    HorseProfileConnector,
    JockeyActiveListConnector,
)
from infrastructure.prerace_sources.track import TrackStatusConnector


@pytest.mark.asyncio
async def test_entry_meeting_list_connector_builds_expected_request():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/chulmainfo/ChulmaDetailInfoList.do"
        assert request.url.params["Act"] == "02"
        assert request.url.params["Sub"] == "1"
        assert request.url.params["meet"] == "1"
        return httpx.Response(
            200,
            content="<html><meta charset='euc-kr'></html>".encode("euc-kr"),
            headers={"content-type": "text/html"},
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = EntryMeetingListConnector(client=client)

    response = await connector.fetch_raw(meet=1)

    assert response.spec.source_id == "entry_meeting_list"
    assert response.status_code == 200
    assert "charset" in response.text


@pytest.mark.asyncio
async def test_entry_race_card_connector_posts_form_payload():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/chulmainfo/chulmaDetailInfoChulmapyo.do"
        body = request.content.decode()
        assert "meet=3" in body
        assert "rcDate=20260412" in body
        assert "rcNo=7" in body
        return httpx.Response(
            200,
            text="<html>race card</html>",
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = EntryRaceCardConnector(client=client)

    response = await connector.fetch_raw(meet=3, race_date="20260412", race_no=7)

    assert response.spec.source_id == "entry_race_card"
    assert "race card" in response.text


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_error():
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, text="busy", request=request)
        return httpx.Response(200, text="<html>ok</html>", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = EntryChangeConnector(client=client)

    response = await connector.fetch_raw(meet=1)

    assert attempts == 2
    assert response.status_code == 200
    assert response.text == "<html>ok</html>"


@pytest.mark.asyncio
async def test_connector_raises_after_retry_exhaustion():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="down", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = TrackStatusConnector(client=client, max_retries=2)

    with pytest.raises(PublicSourceFetchError, match="track_status"):
        await connector.fetch_raw(meet=1)


@pytest.mark.asyncio
async def test_profile_connectors_build_expected_query_params():
    seen: list[tuple[str, str]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, str(request.url.params)))
        return httpx.Response(200, text="<html>ok</html>", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    horse_connector = HorseProfileConnector(client=client)
    jockey_connector = JockeyActiveListConnector(client=client)

    await horse_connector.fetch_raw(meet=1, horse_no="0020089")
    await jockey_connector.fetch_raw(meet=2)

    assert (
        "/racehorse/ProfileHorsenameKinds.do",
        "meet=1&hrNo=0020089",
    ) in seen
    assert (
        "/jockey/ProfileJockeyListActive.do",
        "Act=08&Sub=1&meet=2",
    ) in seen


def test_infer_response_encoding_defaults_to_euc_kr_for_korean_meta():
    body = "<meta charset='euc-kr'><html></html>".encode("euc-kr")

    assert infer_response_encoding({}, body) == "euc-kr"


def test_validate_meet_rejects_unknown_values():
    connector = EntryMeetingListConnector(
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request: None))
    )

    with pytest.raises(ValueError, match="Unsupported KRA meet"):
        connector.build_request(meet=9)


def test_parse_entry_change_bulletin_extracts_cancellations_and_jockey_changes():
    html = """
    <h2><img alt="말취소" /></h2>
    <table><tbody>
      <tr>
        <th>구분</th><th>경주일자</th><th>경주번호</th><th>출전번호</th>
        <th>마명</th><th>조교사명</th><th>기수명</th><th>사유</th><th>공지시간</th>
      </tr>
      <tr>
        <td>출전제외</td>
        <td>2026/04/26 <span>(일)</span></td>
        <td>1</td>
        <td>10</td>
        <td><a href="javascript:goHorse('0054060','1')">서부위스트</a></td>
        <td><a href="javascript:goTrainer('070165','1')">서인석</a></td>
        <td><a href="javascript:goJockey('080603','1')">김태희</a></td>
        <td>경주로 입장 중 기수 낙마 및 방마</td>
        <td>04/26 10:30</td>
      </tr>
    </tbody></table>
    <h2><img alt="기수변경" /></h2>
    <table><tbody>
      <tr>
        <th>경주일자</th><th>경주번호</th><th>출전번호</th><th>마명</th>
        <th>변경전기수</th><th>중량</th><th>변경후기수</th><th>중량</th>
        <th>사유</th><th>공지시간</th>
      </tr>
      <tr>
        <td>2026/04/26 <span>(일)</span></td>
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

    notices = parse_entry_change_bulletin_html(
        html,
        meet=1,
        source_snapshot_at="2026-04-26T01:00:00+00:00",
    )

    assert len(notices) == 2
    cancellation = notices[0]
    assert cancellation.change_type == "cancelled"
    assert cancellation.notice_category == "출전제외"
    assert cancellation.race_date == "20260426"
    assert cancellation.race_no == 1
    assert cancellation.chul_no == 10
    assert cancellation.horse_no == "0054060"
    assert cancellation.jockey_no == "080603"
    assert cancellation.announced_at == "2026-04-26T10:30:00+09:00"

    jockey_change = notices[1]
    assert jockey_change.change_type == "jockey_change"
    assert jockey_change.race_no == 4
    assert jockey_change.chul_no == 7
    assert jockey_change.old_jockey_no == "080111"
    assert jockey_change.new_jockey_no == "080222"
    assert jockey_change.reason == "부상"
    assert jockey_change.meet == 1
    assert jockey_change.source_snapshot_at == "2026-04-26T01:00:00+00:00"


def test_parse_entry_change_bulletin_ignores_empty_notice_rows():
    html = """
    <h2><img alt="기수변경" /></h2>
    <table><tbody>
      <tr><td colspan="10">기수 변경  자료가 없습니다.</td></tr>
    </tbody></table>
    """

    assert parse_entry_change_bulletin_html(html) == ()

from datetime import date
from html import escape

import pytest

from autoresearch.kra_daily_workout_navigation import (
    ALL_LABEL,
    all_detail_request,
    dated_group_request,
)
from autoresearch.kra_daily_workout_source import (
    COUNT_LABEL,
    DATE_LABEL,
    GROUP_CAPTION,
    GROUPS,
    INDEX_CAPTION,
    MENU_ACT,
    ORDER,
    TRAINER_LABEL,
    index_path,
)

DAY = date(2026, 11, 22)
EVENT, WEEKDAY = "2026/11/22", "\uc77c"
HEADS, GROUP = "\ub450", "\uc870"
DAY_ANCHOR = (
    f"<a href=\"#KRA\" onclick=\"javascript:goPage1('{EVENT}', '{WEEKDAY}')\">"
    f"{EVENT}({WEEKDAY})</a>"
)
ALL_BUTTON = (
    '<button type="button" onclick="javascript:goPage2();">'
    f"<span>{ALL_LABEL}</span></button>"
)
GROUP_SCRIPT = """
<script>
function goPage1(trDate, trYo){
    var form = document.form1;
    form.trDate.value = trDate;
    form.trYo.value = trYo;
    // Publisher's comment.
    form.action = "dailyGroupTrainList.do";
    form.submit();
}
</script>
"""
DETAIL_SCRIPT = """
<script>
function goPage2() {
    document.form1.action = "dailyAllTrainDetail.do";
    document.form1.submit();
}
</script>
"""


def _form(lane, action, body, **special):
    fields = {"Act": MENU_ACT[lane], "Sub": "3", "meet": str(lane)} | special
    inputs = "".join(
        f'<input type="hidden" name="{k}" value="{v}">' for k, v in fields.items()
    )
    return (
        f'<form name="form1" method="post" action="{escape(action)}">'
        f"{inputs}{body}</form>"
    )


def _table(caption, headings, cells):
    markup = "".join(f"<th>{x}</th>" for x in headings)
    content = "".join(f"<td>{x}</td>" for x in cells)
    return f"<table><caption>{caption}</caption><tr>{markup}</tr><tr>{content}</tr></table>"


def _index(lane, anchor=DAY_ANCHOR):
    body = _table(
        INDEX_CAPTION, (ORDER, DATE_LABEL, COUNT_LABEL), (1, anchor, "5" + HEADS)
    )
    return GROUP_SCRIPT + _form(
        lane,
        index_path(lane),
        body,
        trDate="",
        trYo="",
        nTotPageRest="4",
        pageIndex="1",
    )


def _groups(lane, button=ALL_BUTTON):
    body = _table(
        GROUP_CAPTION,
        (TRAINER_LABEL, COUNT_LABEL) * 2,
        (f"1{GROUP}(Trainer)", "5" + HEADS, "", ""),
    )
    return DETAIL_SCRIPT + _form(
        lane,
        GROUPS,
        body + button,
        trDate=EVENT,
        trDateReplace="20261122",
        trName="",
        trNo="",
        trYo="??",
    )


@pytest.mark.parametrize("lane", [1, 2, 3])
def test_exact_visible_controls_across_menu_lanes(lane):
    form, n = dated_group_request(_index(lane), DAY, lane=lane)
    assert (form["meet"], form["Act"], form["trDate"], form["trYo"]) == (
        str(lane),
        MENU_ACT[lane],
        EVENT,
        WEEKDAY,
    )
    fields, groups = all_detail_request(_groups(lane), DAY, lane=lane, expected_count=n)
    assert fields["trDateReplace"] == "20261122" and fields["trYo"] == "??"
    assert fields["trNo"] == fields["trName"] == ""
    assert groups == {1: 5}


def test_index_without_requested_day_does_not_authorize_another_date():
    with pytest.raises(ValueError, match="workout_date_not_listed_unconfirmed"):
        dated_group_request(_index(1), date(2026, 11, 21), lane=1)


@pytest.mark.parametrize(
    "anchor",
    [
        f"{EVENT}({WEEKDAY})",
        DAY_ANCHOR.replace("goPage1", "goPage2"),
        DAY_ANCHOR.replace("#KRA", "/another/link"),
    ],
)
def test_date_label_alone_or_mismatched_navigation_is_not_a_control(anchor):
    with pytest.raises(ValueError, match="unverified_workout_control"):
        dated_group_request(_index(1, anchor), DAY, lane=1)


def test_distinguishes_wrong_form_page_and_duplicate_date_controls():
    with pytest.raises(ValueError, match="unverified_workout_date_fields"):
        dated_group_request(
            _index(1).replace(
                'name="pageIndex" value="1"', 'name="pageIndex" value="2"'
            ),
            DAY,
            lane=1,
        )
    with pytest.raises(ValueError, match="unverified_workout_control"):
        dated_group_request(
            _index(1).replace("</form>", DAY_ANCHOR + "</form>"), DAY, lane=1
        )


@pytest.mark.parametrize(
    "button",
    [
        "",
        ALL_BUTTON + ALL_BUTTON,
        ALL_BUTTON.replace("<button ", "<button disabled "),
        ALL_BUTTON.replace(ALL_LABEL, "Trainer only"),
    ],
)
def test_no_detail_request_without_unique_enabled_all_selection(button):
    with pytest.raises(ValueError, match="unverified_workout_control"):
        all_detail_request(_groups(2, button), DAY, lane=2, expected_count=5)


def test_group_totals_and_scope_matched_before_request():
    with pytest.raises(ValueError, match="workout_group_count_changed_since_index"):
        all_detail_request(_groups(3), DAY, lane=3, expected_count=6)
    with pytest.raises(ValueError, match="workout_group_date_mismatch"):
        all_detail_request(
            _groups(3).replace("20261122", "20261121"), DAY, lane=3, expected_count=5
        )
    with pytest.raises(ValueError, match="unverified_workout_all_detail_fields"):
        all_detail_request(
            _groups(3).replace('name="trNo" value=""', 'name="trNo" value="11"'),
            DAY,
            lane=3,
            expected_count=5,
        )


def test_requires_the_observed_submit_body_not_text_in_a_comment_or_foreign_action():
    with pytest.raises(ValueError, match="unverified_workout_submit_action"):
        all_detail_request(
            _groups(3).replace(
                "    document.form1.submit();", "    // document.form1.submit();"
            ),
            DAY,
            lane=3,
            expected_count=5,
        )
    with pytest.raises(ValueError, match="unverified_workout_submit_action"):
        dated_group_request(
            _index(1).replace("dailyGroupTrainList.do", "differentRoute.do"),
            DAY,
            lane=1,
        )

"""Physical KRA race identities, independent of any source's supported layout."""

import re
from datetime import datetime

MEET_NAMES = {
    "\uc11c\uc6b8": 1,
    "\uc81c\uc8fc": 2,
    "\ubd80\uacbd": 3,
    "\ubd80\uc0b0\uacbd\ub0a8": 3,
    "\uc601\ucc9c": 4,
}
_MEET_CODES = frozenset(MEET_NAMES.values())


def validate_race_identity(meet: int, race_date: str, race_no: int) -> None:
    if type(meet) is not int or meet not in _MEET_CODES:
        raise ValueError(
            "meet must be 1 (Seoul), 2 (Jeju), 3 (Busan), or 4 (Yeongcheon)"
        )
    if type(race_no) is not int or not 1 <= race_no <= 20:
        raise ValueError("race_no must be an integer between 1 and 20")
    if not isinstance(race_date, str) or not re.fullmatch(r"20[0-9]{6}", race_date):
        raise ValueError("race_date must be YYYYMMDD within 2000-2099")
    datetime.strptime(race_date, "%Y%m%d")

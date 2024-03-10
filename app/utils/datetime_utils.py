from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

# 한국
tzinfo = ZoneInfo("Asia/Seoul")


def getNow():
    today = datetime.now(tz=tzinfo)
    return today


def afterMinutes(target: datetime, minutes: int):
    return target + timedelta(minutes=minutes)


def afterHours(target: datetime, hours: int):
    return target + timedelta(hours=hours)


def beforeHours(target: datetime, hours: int):
    return target - timedelta(hours=hours)

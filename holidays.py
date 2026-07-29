"""
中国公众假期定义 (2025-2026)
用于判断工作日/节假日
"""
from datetime import date, timedelta

# 2025年中国公众假期
HOLIDAYS_2025 = {
    # 元旦
    date(2025, 1, 1),
    # 春节
    date(2025, 1, 28), date(2025, 1, 29), date(2025, 1, 30),
    date(2025, 1, 31), date(2025, 2, 1), date(2025, 2, 2),
    date(2025, 2, 3), date(2025, 2, 4),
    # 清明节
    date(2025, 4, 4), date(2025, 4, 5), date(2025, 4, 6),
    # 劳动节
    date(2025, 5, 1), date(2025, 5, 2), date(2025, 5, 3),
    date(2025, 5, 4), date(2025, 5, 5),
    # 端午节
    date(2025, 5, 31), date(2025, 6, 1), date(2025, 6, 2),
    # 中秋节+国庆节
    date(2025, 10, 1), date(2025, 10, 2), date(2025, 10, 3),
    date(2025, 10, 4), date(2025, 10, 5), date(2025, 10, 6),
    date(2025, 10, 7), date(2025, 10, 8),
}

# 2026年中国公众假期 (预估，实际以国务院通知为准)
HOLIDAYS_2026 = {
    # 元旦
    date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3),
    # 春节 (预估 2/16-2/22)
    date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18),
    date(2026, 2, 19), date(2026, 2, 20), date(2026, 2, 21),
    date(2026, 2, 22),
    # 清明节 (预估 4/4-4/6)
    date(2026, 4, 4), date(2026, 4, 5), date(2026, 4, 6),
    # 劳动节 (预估 5/1-5/5)
    date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3),
    date(2026, 5, 4), date(2026, 5, 5),
    # 端午节 (预估 6/19-6/21)
    date(2026, 6, 19), date(2026, 6, 20), date(2026, 6, 21),
    # 中秋节 (预估 9/25-9/27)
    date(2026, 9, 25), date(2026, 9, 26), date(2026, 9, 27),
    # 国庆节 (预估 10/1-10/7)
    date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3),
    date(2026, 10, 4), date(2026, 10, 5), date(2026, 10, 6),
    date(2026, 10, 7),
}

ALL_HOLIDAYS = HOLIDAYS_2025 | HOLIDAYS_2026


def is_holiday(d):
    """判断是否为假期(周末或公众假期)"""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    if d.weekday() >= 5:  # 周六周日
        return True
    if d in ALL_HOLIDAYS:
        return True
    return False


def is_workday(d):
    """判断是否为工作日"""
    return not is_holiday(d)


def get_last_workday_of_month(year, month):
    """获取当月最后一个工作日"""
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    d = next_month - timedelta(days=1)
    while is_holiday(d):
        d -= timedelta(days=1)
    return d


def get_first_workday_of_month(year, month):
    """获取当月第一个工作日(如果1号是假期，取上月最后一个工作日)"""
    d = date(year, month, 1)
    if is_holiday(d):
        # 月初遇假期，取上个月最后一个工作日
        if month == 1:
            d = date(year - 1, 12, 31)
        else:
            d = date(year, month, 1) - timedelta(days=1)
        while is_holiday(d):
            d -= timedelta(days=1)
    return d

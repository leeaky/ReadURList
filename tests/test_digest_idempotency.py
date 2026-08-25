from datetime import date

from second_read.rank.digest import should_send_digest


def test_digest_sends_when_no_run_today():
    assert should_send_digest(existing_run_on=None, today=date(2026, 8, 20)) is True


def test_digest_does_not_send_twice_same_day():
    today = date(2026, 8, 20)
    assert should_send_digest(existing_run_on=today, today=today) is False


def test_digest_sends_on_a_new_day():
    assert (
        should_send_digest(existing_run_on=date(2026, 8, 19), today=date(2026, 8, 20))
        is True
    )

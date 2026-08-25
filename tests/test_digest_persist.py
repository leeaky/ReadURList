from datetime import date

from second_read.db import DigestRun, get_session, init_db
from second_read.rank.run import _existing_digest_run, _record_digest_run


def test_digest_run_row_inserted_once(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    today = date(2026, 8, 20)
    _record_digest_run(today)
    _record_digest_run(today)
    session = get_session()
    try:
        assert session.query(DigestRun).filter_by(run_on=today).count() == 1
        assert _existing_digest_run(today) == today
    finally:
        session.close()

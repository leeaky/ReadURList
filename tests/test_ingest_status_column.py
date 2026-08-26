from second_read.db import Item, get_session, init_db


def test_new_item_defaults_ingest_status_ready(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    session = get_session()
    try:
        item = Item(url="https://example.com/a", title="A")
        session.add(item)
        session.commit()
        session.refresh(item)
        assert item.ingest_status == "ready"
    finally:
        session.close()

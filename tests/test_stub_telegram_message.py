from second_read.bot.handlers import format_stub_ack


def test_format_stub_ack_includes_unfetched_link():
    text = format_stub_ack("https://readurlist.example")
    assert "could not be retrieved" in text.lower() or "could not retrieve" in text.lower()
    assert "https://readurlist.example/unfetched" in text


def test_format_stub_ack_without_site_url():
    text = format_stub_ack("")
    assert "unfetched" in text.lower()
    assert "http" not in text  # no broken link

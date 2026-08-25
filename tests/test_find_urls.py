from second_read.ingest.extract import find_urls


def test_find_urls_extracts_several_in_one_message():
    text = "https://example.com/a and https://example.org/b"
    assert find_urls(text) == ["https://example.com/a", "https://example.org/b"]

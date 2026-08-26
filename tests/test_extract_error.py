import pytest

from second_read.ingest.extract import ExtractError, extract_article


def test_short_html_raises_extract_error_with_title(monkeypatch):
    html = "<html><head><title>Paywalled Piece</title></head><body>Hi</body></html>"

    def fake_fetch(url: str, timeout: float) -> str:
        return html

    monkeypatch.setattr("second_read.ingest.extract._fetch_html", fake_fetch)

    with pytest.raises(ExtractError) as excinfo:
        extract_article("https://example.com/paywall")

    assert excinfo.value.title == "Paywalled Piece"
    assert "enough article text" in str(excinfo.value).lower() or "extract" in str(excinfo.value).lower()

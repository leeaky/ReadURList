import pytest
from test_arxiv import _pdf, _transport

from readurlist.ingest import arxiv
from readurlist.ingest.arxiv import pdf_word_count
from readurlist.ingest.extract import pdf_link


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        ('<meta name="citation_pdf_url" content="https://journal.org/a.pdf">', "https://journal.org/a.pdf"),
        ("<META NAME='citation_pdf_url' CONTENT='/content/a.full.pdf'>", "https://site.org/content/a.full.pdf"),
        ('<meta content="https://journal.org/a.pdf" name="citation_pdf_url" />', "https://journal.org/a.pdf"),
        ('<meta name="citation_title" content="A paper">', None),
        ('<meta name="citation_pdf_url" content="">', None),
        ('<meta name="citation_pdf_url" content="javascript:alert(1)">', None),
        ("<p>no tags</p>", None),
    ],
)
def test_pdf_link(html, expected):
    assert pdf_link(f"<html><head>{html}</head></html>", "https://site.org/doi/10.1/x") == expected


PAGE = "https://journal.org/doi/10.1/x"
PDF = "https://journal.org/doi/pdf/10.1/x"


def test_pdf_word_count_reads_any_pdf(monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(arxiv, "_TRANSPORT", _transport(_pdf("one two three"), seen))
    assert pdf_word_count(PDF, page_url=PAGE) == 3
    assert seen == [PDF]


def test_a_blocked_pdf_is_one_plain_line(monkeypatch, caplog):
    monkeypatch.setattr(arxiv, "_TRANSPORT", _transport(None, []))
    with caplog.at_level("WARNING"):
        assert pdf_word_count(PDF, page_url=PAGE) is None
    assert [r.getMessage() for r in caplog.records if r.name.startswith("readurlist")] == [
        f"Paper {PAGE} (PDF {PDF}): PDF not found (HTTP 404); counted as 45 min"
    ]


def test_extract_article_returns_the_pdf_link(monkeypatch):
    from readurlist.ingest.extract import extract_article

    body = "<p>" + "We study compost in gardens. " * 20 + "</p>"
    html = f'<html><head><title>A paper</title><meta name="citation_pdf_url" content="/pdf/x"></head><body><article>{body}</article></body></html>'
    monkeypatch.setattr("readurlist.ingest.extract._fetch_html", lambda url, timeout: html)
    title, text, pdf = extract_article(PAGE)
    assert "compost" in text
    assert pdf == "https://journal.org/pdf/x"


def _ingest(tmp_path, monkeypatch, pdf, count):
    from test_arxiv import ABSTRACT, OneAnswerLLM, _settings

    from readurlist.db import init_db
    from readurlist.ingest import ingest_url

    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    monkeypatch.setattr("readurlist.ingest.extract_article", lambda url, timeout=30.0: ("T", ABSTRACT, pdf))
    asked: list[tuple[str, str]] = []

    def fake_count(pdf_url, *, page_url):
        asked.append((pdf_url, page_url))
        return count

    monkeypatch.setattr("readurlist.ingest.pdf_word_count", fake_count)
    item, _ = ingest_url(PAGE, OneAnswerLLM(), _settings(db))  # type: ignore[arg-type]
    return item, asked


def test_a_paper_page_takes_its_length_from_its_pdf(tmp_path, monkeypatch):
    item, asked = _ingest(tmp_path, monkeypatch, PDF, 9000)
    assert asked == [(PDF, PAGE)]
    assert item.word_count == 9000
    assert "We study compost." in item.extracted_text  # the page's text is kept, not the PDF's


def test_a_paper_page_counts_as_45_min_when_the_pdf_fails(tmp_path, monkeypatch):
    from readurlist.effort import effort

    item, _ = _ingest(tmp_path, monkeypatch, PDF, None)
    assert item.word_count == 45 * 230  # owner, 2026-11-01: a paper is long; stand-in length
    assert effort(item.word_count) == ("long", 45)


def test_a_page_without_the_tag_fetches_no_pdf(tmp_path, monkeypatch):
    item, asked = _ingest(tmp_path, monkeypatch, None, 9000)
    assert asked == []
    assert item.word_count == 120


def test_one_off_fix_rechecks_short_paper_pages(tmp_path, monkeypatch, caplog):
    from test_arxiv import ABSTRACT

    from readurlist.db import Item, get_session, init_db
    from readurlist.ingest.arxiv import fix_saved_paper_pages
    from readurlist.ingest.extract import FetchError

    init_db(f"sqlite:///{tmp_path / 't.db'}")
    session = get_session()
    for url, status, words in [
        ("https://journal.org/paper", "ready", 120),  # Short, has a tag: fixed
        ("https://blog.org/post", "ready", 900),  # Short, no tag: left alone
        ("https://journal.org/blocked", "ready", 150),  # Short, PDF blocked: 45 min stand-in
        ("https://gone.org/page", "ready", 200),  # Short, page gone: kept
        ("https://journal.org/long", "ready", 5000),  # Long: not rechecked
        ("https://arxiv.org/abs/2410.00001", "ready", 120),  # arXiv: stage 11's fix
        ("https://journal.org/pending", "pending_body", 120),  # not ready
    ]:
        session.add(Item(url=url, title="T", snapshot="s", subject="a", topics=[], keywords=[],
                         extracted_text=ABSTRACT, priority=3, ingest_status=status, word_count=words))
    session.commit()
    session.close()
    tag = '<meta name="citation_pdf_url" content="{}">'
    pages = {
        "https://journal.org/paper": tag.format("/paper.pdf"),
        "https://blog.org/post": "<p>no tag</p>",
        "https://journal.org/blocked": tag.format("/blocked.pdf"),
    }
    fetched: list[str] = []

    def fake_fetch(url, timeout):
        fetched.append(url)
        if url not in pages:
            raise FetchError("Could not fetch page (HTTP 404).", status_code=404)
        return pages[url]

    monkeypatch.setattr("readurlist.ingest.extract._fetch_html", fake_fetch)
    counts = {"https://journal.org/paper.pdf": 8000, "https://journal.org/blocked.pdf": None}
    monkeypatch.setattr(arxiv, "pdf_word_count", lambda pdf_url, *, page_url: counts[pdf_url])
    waits: list[float] = []

    with caplog.at_level("WARNING"):
        result = fix_saved_paper_pages(sleep=waits.append)

    assert "Paper https://gone.org/page: page could not be fetched (HTTP 404); kept the page count" in [
        r.getMessage() for r in caplog.records
    ]
    assert result == (1, 1, 1, 1)  # counted from their PDF, counted as 45 min, no PDF tag, kept the page count
    assert fetched == ["https://journal.org/paper", "https://blog.org/post",
                       "https://journal.org/blocked", "https://gone.org/page"]
    assert waits == [2.0, 2.0, 2.0]
    session = get_session()
    words = {i.url: i.word_count for i in session.query(Item)}
    session.close()
    assert words["https://journal.org/paper"] == 8000
    assert words["https://blog.org/post"] == 900
    assert words["https://journal.org/blocked"] == 45 * 230
    assert words["https://gone.org/page"] == 200

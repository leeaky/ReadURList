import json

import httpx
import pytest

from readurlist.config import Settings
from readurlist.db import init_db
from readurlist.ingest import ingest_url
from readurlist.ingest import arxiv
from readurlist.ingest.arxiv import abs_url, arxiv_id, paper_word_count

ABSTRACT = "We study compost. " * 40  # 120 words: the abstract page alone reads as short


def _pdf(text: str) -> bytes:
    """A one-page PDF whose page shows `text`."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for n, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://arxiv.org/abs/2410.12345", "2410.12345"),
        ("https://arxiv.org/abs/2410.12345v2", "2410.12345v2"),
        ("https://arxiv.org/pdf/2410.12345", "2410.12345"),
        ("https://arxiv.org/pdf/2410.12345v3.pdf", "2410.12345v3"),
        ("https://arxiv.org/html/2410.12345v1", "2410.12345v1"),
        ("http://export.arxiv.org/abs/2410.12345", "2410.12345"),
        ("https://www.arxiv.org/abs/hep-th/9901001", "hep-th/9901001"),
        ("https://example.com/abs/2410.12345", None),
        ("https://arxiv.org/list/cs.AI/recent", None),
    ],
)
def test_arxiv_id(url, expected):
    assert arxiv_id(url) == expected


def test_abs_url():
    assert abs_url("2410.12345v2") == "https://arxiv.org/abs/2410.12345v2"


def _transport(pdf: bytes | None, seen: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if pdf is None:
            return httpx.Response(404)
        return httpx.Response(200, content=pdf, headers={"content-type": "application/pdf"})

    return httpx.MockTransport(handler)


def test_paper_word_count_reads_the_pdf(monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(arxiv, "_TRANSPORT", _transport(_pdf("one two three four five"), seen))
    assert paper_word_count("2410.12345") == 5
    assert seen == ["https://arxiv.org/pdf/2410.12345"]


def test_paper_word_count_is_none_when_the_pdf_fails(monkeypatch):
    monkeypatch.setattr(arxiv, "_TRANSPORT", _transport(None, []))
    assert paper_word_count("2410.12345") is None
    monkeypatch.setattr(arxiv, "_TRANSPORT", _transport(b"not a pdf", []))
    assert paper_word_count("2410.12345") is None


class OneAnswerLLM:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def complete(self, prompt, *, model, system=None, schema=None, temperature=0.3) -> str:
        self.prompts.append(prompt)
        return json.dumps({"title": "T", "snapshot": "Summary.", "subject": "Gardening",
                           "topics": ["soil"], "keywords": ["compost"], "priority": 3})


def _settings(db: str) -> Settings:
    return Settings(telegram_bot_token="x", telegram_user_id=1, groq_api_key="x", database_url=db)


def test_arxiv_link_takes_its_length_from_the_paper(tmp_path, monkeypatch):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    fetched: list[str] = []

    def fake_extract(url, timeout=30.0):
        fetched.append(url)
        return "Compost paper", ABSTRACT

    monkeypatch.setattr("readurlist.ingest.extract_article", fake_extract)
    monkeypatch.setattr("readurlist.ingest.paper_word_count", lambda paper_id: 9000)
    llm = OneAnswerLLM()

    item, created = ingest_url("https://arxiv.org/pdf/2410.12345v2", llm, _settings(db))  # type: ignore[arg-type]

    assert created and item.ingest_status == "ready"
    assert fetched == ["https://arxiv.org/abs/2410.12345v2"]  # title and summary from the abstract page
    assert item.url == "https://arxiv.org/pdf/2410.12345v2"
    assert item.word_count == 9000
    assert item.extracted_text == ABSTRACT  # the paper's text isn't stored
    assert "We study compost." in llm.prompts[0]


def test_arxiv_link_keeps_the_abstract_count_when_the_paper_fails(tmp_path, monkeypatch):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    monkeypatch.setattr("readurlist.ingest.extract_article", lambda url, timeout=30.0: ("T", ABSTRACT))
    monkeypatch.setattr("readurlist.ingest.paper_word_count", lambda paper_id: None)

    item, _ = ingest_url("https://arxiv.org/abs/2410.12345", OneAnswerLLM(), _settings(db))  # type: ignore[arg-type]

    assert item.word_count == 120


def test_other_links_do_not_fetch_a_paper(tmp_path, monkeypatch):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    monkeypatch.setattr("readurlist.ingest.extract_article", lambda url, timeout=30.0: ("T", ABSTRACT))

    def boom(paper_id):
        raise AssertionError("no paper fetch for ordinary links")

    monkeypatch.setattr("readurlist.ingest.paper_word_count", boom)
    item, _ = ingest_url("https://example.com/a", OneAnswerLLM(), _settings(db))  # type: ignore[arg-type]
    assert item.word_count == 120


def test_one_off_fix_counts_saved_papers_from_their_pdf(tmp_path, monkeypatch):
    from readurlist.db import Item, get_session
    from readurlist.ingest.arxiv import fix_saved_papers

    init_db(f"sqlite:///{tmp_path / 't.db'}")
    session = get_session()
    for url, status in [
        ("https://arxiv.org/abs/2410.00001", "ready"),
        ("https://arxiv.org/abs/2410.00002", "ready"),  # its PDF fails
        ("https://arxiv.org/abs/2410.00003", "pending_body"),  # not ready: left alone
        ("https://example.com/a", "ready"),
    ]:
        session.add(Item(url=url, title="T", snapshot="s", subject="a", topics=[], keywords=[],
                         extracted_text=ABSTRACT, priority=3, ingest_status=status, word_count=120))
    session.commit()
    session.close()
    counts = {"2410.00001": 8000, "2410.00002": None}
    asked: list[str] = []

    def fake_count(paper_id):
        asked.append(paper_id)
        return counts[paper_id]

    monkeypatch.setattr(arxiv, "paper_word_count", fake_count)
    waits: list[float] = []

    fixed, failed = fix_saved_papers(sleep=waits.append)

    assert (fixed, failed) == (1, 1)
    assert asked == ["2410.00001", "2410.00002"]
    assert waits == [3.0]  # arXiv asks for a pause between requests
    session = get_session()
    words = {i.url: i.word_count for i in session.query(Item)}
    session.close()
    assert words["https://arxiv.org/abs/2410.00001"] == 8000
    assert words["https://arxiv.org/abs/2410.00002"] == 120
    assert words["https://example.com/a"] == 120


def test_a_missing_pdf_is_one_plain_line(monkeypatch, caplog):
    monkeypatch.setattr(arxiv, "_TRANSPORT", _transport(None, []))
    with caplog.at_level("WARNING"):
        assert paper_word_count("2608.00858") is None
    lines = [r for r in caplog.records if r.name.startswith("readurlist")]
    assert [r.getMessage() for r in lines] == [
        "arXiv 2608.00858 (https://arxiv.org/abs/2608.00858): PDF not found (HTTP 404); kept the abstract count"
    ]
    assert all(r.exc_info is None for r in lines)  # no traceback


def test_a_pdf_without_text_says_so(monkeypatch, caplog):
    monkeypatch.setattr(arxiv, "_TRANSPORT", _transport(_pdf(""), []))
    with caplog.at_level("WARNING"):
        assert paper_word_count("2410.12345") is None
    assert [r.getMessage() for r in caplog.records if r.name.startswith("readurlist")] == [
        "arXiv 2410.12345 (https://arxiv.org/abs/2410.12345): no text in the PDF; kept the abstract count"
    ]


def test_pdf_reader_notes_are_hidden():
    import logging

    assert logging.getLogger("pypdf").getEffectiveLevel() > logging.ERROR

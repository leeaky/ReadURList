from __future__ import annotations

from datetime import datetime, timedelta, timezone

from second_read.rank.score import RankItem, cluster_items, score_unread

NOW = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)


def _item(
    id: int,
    *,
    subject: str = "ai",
    topics: list[str] | None = None,
    keywords: list[str] | None = None,
    days_ago: int = 1,
    read: bool = False,
    priority: int = 3,
) -> RankItem:
    created = NOW - timedelta(days=days_ago)
    return RankItem(
        id=id,
        subject=subject,
        topics=topics or [subject],
        keywords=keywords or [subject, f"kw{id}"],
        created_at=created,
        read_at=created if read else None,
        priority=priority,
    )


def test_ranking_uses_unread_only():
    items = [
        _item(1, subject="ai", read=False),
        _item(2, subject="ai", read=True),
        _item(3, subject="ai", read=False),
    ]
    picks = score_unread(items, now=NOW, top_n=5)
    assert {p.item_id for p in picks} <= {1, 3}
    assert 2 not in {p.item_id for p in picks}


def test_diversity_cap_at_most_two_per_subject():
    items = [_item(i, subject="ai", days_ago=i) for i in range(1, 8)]
    items += [_item(10, subject="climate", days_ago=1)]
    items += [_item(11, subject="climate", days_ago=2)]
    picks = score_unread(items, now=NOW, top_n=5)
    by_subject: dict[str, int] = {}
    for p in picks:
        item = next(i for i in items if i.id == p.item_id)
        by_subject[item.subject] = by_subject.get(item.subject, 0) + 1
    assert all(n <= 2 for n in by_subject.values())
    assert len(picks) <= 5


def test_duplicate_of_already_read_is_omitted():
    read = _item(
        1,
        subject="llms",
        keywords=["transformer", "attention", "gpt"],
        topics=["llms"],
        read=True,
    )
    dup = _item(
        2,
        subject="llms",
        keywords=["transformer", "attention", "gpt"],
        topics=["llms"],
        read=False,
        days_ago=0,
    )
    other = _item(
        3,
        subject="climate",
        keywords=["carbon", "warming"],
        topics=["climate"],
        read=False,
        days_ago=0,
    )
    picks = score_unread([read, dup, other], now=NOW, top_n=5)
    assert 2 not in {p.item_id for p in picks}
    assert 3 in {p.item_id for p in picks}


def test_near_duplicate_unread_is_buried_behind_canonical():
    a = _item(
        1,
        subject="llms",
        keywords=["transformer", "attention", "gpt", "openai"],
        topics=["llms", "nlp"],
        days_ago=2,
        priority=5,
    )
    b = _item(
        2,
        subject="llms",
        keywords=["transformer", "attention", "gpt", "openai"],
        topics=["llms", "nlp"],
        days_ago=0,
        priority=2,
    )
    c = _item(
        3,
        subject="climate",
        keywords=["ice", "antarctica"],
        topics=["climate"],
        days_ago=1,
        priority=4,
    )
    d = _item(
        4,
        subject="markets",
        keywords=["rates", "bonds"],
        topics=["finance"],
        days_ago=1,
        priority=4,
    )
    picks = score_unread([a, b, c, d], now=NOW, top_n=3)
    ids = [p.item_id for p in picks]
    assert 1 in ids
    assert 2 not in ids


def test_path_novelty_boosts_unseen_subject():
    path = [
        _item(1, subject="ai", keywords=["llm", "gpt"], topics=["ai"], read=True, days_ago=3),
        _item(2, subject="ai", keywords=["llm", "agents"], topics=["ai"], read=True, days_ago=2),
    ]
    same = _item(3, subject="ai", keywords=["llm", "eval"], topics=["ai"], days_ago=0, priority=3)
    novel = _item(
        4,
        subject="housing",
        keywords=["rent", "zoning"],
        topics=["housing"],
        days_ago=0,
        priority=3,
    )
    picks = score_unread(path + [same, novel], now=NOW, top_n=1)
    assert picks[0].item_id == 4


def test_top_n_stable_for_same_fixture():
    items = [
        _item(i, subject="s" + str(i % 3), keywords=[f"k{i}", "shared"], days_ago=i, priority=3)
        for i in range(1, 12)
    ]
    first = [p.item_id for p in score_unread(items, now=NOW, top_n=5)]
    second = [p.item_id for p in score_unread(items, now=NOW, top_n=5)]
    assert first == second
    assert len(first) == 5


def test_picks_include_nonempty_reason():
    items = [_item(1), _item(2, subject="other")]
    picks = score_unread(items, now=NOW, top_n=5)
    assert picks
    assert all(p.reason.strip() for p in picks)


def test_mark_as_read_removes_from_unread_pool():
    item = _item(1, read=False)
    assert score_unread([item], now=NOW, top_n=5)
    item.read_at = NOW
    assert score_unread([item], now=NOW, top_n=5) == []


def test_clearing_read_at_returns_item_to_pool():
    item = _item(1, read=True)
    assert score_unread([item], now=NOW, top_n=5) == []
    item.read_at = None
    assert [p.item_id for p in score_unread([item], now=NOW, top_n=5)] == [1]


def test_clusters_group_similar_keywords():
    items = [
        _item(1, subject="llms", keywords=["gpt", "openai", "transformer"], topics=["ai"]),
        _item(2, subject="llms", keywords=["gpt", "openai", "chat"], topics=["ai"]),
        _item(3, subject="climate", keywords=["ice", "melt"], topics=["climate"]),
    ]
    clusters = cluster_items(items, threshold=0.3)
    assert len(clusters) >= 2
    llm_cluster = next(c for c in clusters if 1 in c.item_ids)
    assert 2 in llm_cluster.item_ids
    assert 3 not in llm_cluster.item_ids

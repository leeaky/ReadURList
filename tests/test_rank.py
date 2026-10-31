from __future__ import annotations

from datetime import datetime, timedelta, timezone

from readurlist.rank.score import RankItem, build_day_list

NOW = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)


def score_unread(items, *, now):
    return build_day_list(items, now=now).picks


def _item(
    id: int,
    *,
    subject: str = "ai",
    topics: list[str] | None = None,
    keywords: list[str] | None = None,
    days_ago: int = 1,
    read: bool = False,
    skipped: bool = False,
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
        skipped_at=created if skipped else None,
    )


def test_ranking_uses_unread_only():
    items = [
        _item(1, subject="ai", read=False),
        _item(2, subject="ai", read=True),
        _item(3, subject="ai", read=False),
    ]
    picks = score_unread(items, now=NOW)
    assert {p.item_id for p in picks} <= {1, 3}
    assert 2 not in {p.item_id for p in picks}


def test_diversity_cap_at_most_two_per_subject():
    items = [_item(i, subject="ai", days_ago=i) for i in range(1, 8)]
    items += [_item(10, subject="climate", days_ago=1)]
    items += [_item(11, subject="climate", days_ago=2)]
    picks = score_unread(items, now=NOW)
    by_subject: dict[str, int] = {}
    for p in picks:
        item = next(i for i in items if i.id == p.item_id)
        by_subject[item.subject] = by_subject.get(item.subject, 0) + 1
    assert all(n <= 2 for n in by_subject.values())
    assert len(picks) <= 5


def test_unread_with_overlapping_tags_of_read_item_still_ranks():
    read = _item(
        1,
        subject="llms",
        keywords=["transformer", "attention", "gpt"],
        topics=["llms"],
        read=True,
    )
    overlapping = _item(
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
    picks = score_unread([read, overlapping, other], now=NOW)
    assert {p.item_id for p in picks} == {2, 3}


def test_two_unread_with_overlapping_tags_can_both_rank():
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
    picks = score_unread([a, b, c], now=NOW)
    assert {p.item_id for p in picks} == {1, 2, 3}


def test_top_n_stable_for_same_fixture():
    items = [
        _item(i, subject="s" + str(i % 3), keywords=[f"k{i}", "shared"], days_ago=i, priority=3)
        for i in range(1, 12)
    ]
    first = [p.item_id for p in score_unread(items, now=NOW)]
    second = [p.item_id for p in score_unread(items, now=NOW)]
    assert first == second
    assert len(first) == 3  # no word counts here, so all short: 3 short picks


def test_picks_include_nonempty_reason():
    items = [_item(1), _item(2, subject="other")]
    picks = score_unread(items, now=NOW)
    assert picks
    assert all(p.reason.strip() for p in picks)


def test_mark_as_read_removes_from_unread_pool():
    item = _item(1, read=False)
    assert score_unread([item], now=NOW)
    item.read_at = NOW
    assert score_unread([item], now=NOW) == []


def test_clearing_read_at_returns_item_to_pool():
    item = _item(1, read=True)
    assert score_unread([item], now=NOW) == []
    item.read_at = None
    assert [p.item_id for p in score_unread([item], now=NOW)] == [1]


def test_score_has_two_parts_subject_65_and_recency_35():
    import readurlist.rank.score as score

    assert (score.SUBJECT_POINTS, score.RECENCY_POINTS) == (65, 35)
    for gone in ("W_NOVELTY", "W_PRIORITY", "_path_novelty", "_priority_norm"):
        assert not hasattr(score, gone)


def test_points_per_part_add_up_to_the_score():
    items = [_item(1, subject="llms", days_ago=0), _item(2, subject="llms", days_ago=3)]
    items.append(_item(3, subject="climate", days_ago=1))
    for p in score_unread(items, now=NOW):
        assert p.subject_points + p.recency_points == p.score
        assert 0 <= p.subject_points <= 65 and 0 <= p.recency_points <= 35


def test_biggest_subject_gets_all_65_subject_points():
    items = [_item(i, subject="llms", days_ago=2) for i in range(1, 5)]
    items.append(_item(9, subject="climate", days_ago=2))
    picks = {p.item_id: p for p in score_unread(items, now=NOW)}
    assert picks[1].subject_points == 65
    assert picks[9].subject_points == 16  # 1 of 4: 65 / 4 = 16.25


def test_saved_just_now_gets_all_35_recency_points():
    picks = score_unread([_item(1, days_ago=0)], now=NOW)
    assert picks[0].recency_points == 35


def test_reason_names_the_biggest_part_and_shows_the_points():
    items = [_item(i, subject="llms", days_ago=5) for i in range(1, 5)]
    items.append(_item(9, subject="climate", days_ago=0))
    picks = {p.item_id: p for p in score_unread(items, now=NOW)}
    assert picks[1].reason.startswith("You keep saving llms: 4 unread")
    assert "subject 65 + recency 6 = 71" in picks[1].reason
    assert picks[9].reason.startswith("Saved today")
    assert "subject 16 + recency 35 = 51" in picks[9].reason
    assert all("cluster" not in p.reason.lower() for p in picks.values())


def test_restored_item_counts_from_the_restore_date():
    old = _item(1, subject="llms", days_ago=30)
    restored = _item(2, subject="llms", days_ago=30)
    restored.restored_at = NOW
    picks = {p.item_id: p for p in score_unread([old, restored], now=NOW)}
    assert picks[2].recency_points == 35
    assert picks[1].recency_points == 1


def test_two_unread_same_subject_still_cap_at_two():
    a = _item(
        1,
        subject="llms",
        topics=["large language models", "mixture of experts"],
        keywords=["kimi", "k3", "moonshot"],
        priority=5,
    )
    b = _item(
        2,
        subject="llms",
        topics=["large language models", "mixture of experts"],
        keywords=["llada", "diffusion", "qwen"],
        priority=5,
        days_ago=0,
    )
    picks = score_unread([a, b], now=NOW)
    assert {p.item_id for p in picks} == {1, 2}


def test_skipped_item_is_not_ranked():
    skipped = _item(1, skipped=True, priority=5, days_ago=0)
    other = _item(2, subject="climate", days_ago=1)
    picks = score_unread([skipped, other], now=NOW)
    assert [p.item_id for p in picks] == [2]


def test_restoring_skipped_item_returns_it_to_pool():
    item = _item(1, skipped=True)
    assert score_unread([item], now=NOW) == []
    item.skipped_at = None
    assert [p.item_id for p in score_unread([item], now=NOW)] == [1]

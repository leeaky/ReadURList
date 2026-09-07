from readurlist.tags.normalize import canonicalize_label, should_consolidate


def test_canonicalize_keeps_existing_spelling():
    existing = ["Claude Code", "LLM research"]
    assert canonicalize_label("claude code", existing) == "Claude Code"
    assert canonicalize_label("  LLM  research ", existing) == "LLM research"


def test_canonicalize_maps_unicode_dashes_then_matches():
    existing = ["mixture-of-experts"]
    assert canonicalize_label("mixture\u2013of\u2013experts", existing) == "mixture-of-experts"


def test_canonicalize_mints_when_nothing_matches():
    assert canonicalize_label("  Public Health  ", ["Claude Code"]) == "Public Health"


def test_canonicalize_empty_is_empty():
    assert canonicalize_label("   ", ["Claude Code"]) == ""
    assert canonicalize_label(None, []) == ""  # type: ignore[arg-type]


def test_should_consolidate_needs_eight_and_majority_unique():
    assert should_consolidate(ready_count=7, unique_subjects=7) is False
    assert should_consolidate(ready_count=8, unique_subjects=4) is False  # 0.5 not greater
    assert should_consolidate(ready_count=8, unique_subjects=5) is True
    assert should_consolidate(ready_count=31, unique_subjects=31) is True
    assert should_consolidate(ready_count=0, unique_subjects=0) is False

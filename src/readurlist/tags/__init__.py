from readurlist.tags.consolidate import maybe_consolidate_tags
from readurlist.tags.normalize import canonicalize_label, should_consolidate
from readurlist.tags.vocab import Vocabulary, apply_tag_maps, load_vocabulary

__all__ = [
    "Vocabulary",
    "apply_tag_maps",
    "canonicalize_label",
    "load_vocabulary",
    "maybe_consolidate_tags",
    "should_consolidate",
]

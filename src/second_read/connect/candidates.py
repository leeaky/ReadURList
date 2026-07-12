from __future__ import annotations

import json
import logging
import math
from typing import Optional

from second_read.db import Claim, get_session

logger = logging.getLogger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _load_embedding(claim: Claim) -> Optional[list[float]]:
    if not claim.embedding_json:
        return None
    try:
        return json.loads(claim.embedding_json)
    except json.JSONDecodeError:
        return None


def find_candidates(
    new_claim_ids: list[int],
    *,
    top_k_per_claim: int = 5,
    min_similarity: float = 0.55,
) -> list[tuple[int, int, float]]:
    """Return (new_claim_id, old_claim_id, similarity) pairs for labeling."""
    session = get_session()
    try:
        new_claims = session.query(Claim).filter(Claim.id.in_(new_claim_ids)).all()
        if not new_claims:
            return []

        item_ids = {c.item_id for c in new_claims}
        old_claims = session.query(Claim).filter(~Claim.item_id.in_(item_ids)).all()
        if not old_claims:
            return []

        old_with_emb: list[tuple[Claim, list[float]]] = []
        for c in old_claims:
            emb = _load_embedding(c)
            if emb:
                old_with_emb.append((c, emb))

        pairs: list[tuple[int, int, float]] = []
        for nc in new_claims:
            nemb = _load_embedding(nc)
            if not nemb:
                continue
            scored: list[tuple[int, float]] = []
            for oc, oemb in old_with_emb:
                sim = _cosine(nemb, oemb)
                if sim >= min_similarity:
                    scored.append((oc.id, sim))
            scored.sort(key=lambda x: x[1], reverse=True)
            for oid, sim in scored[:top_k_per_claim]:
                pairs.append((nc.id, oid, sim))
        return pairs
    finally:
        session.close()

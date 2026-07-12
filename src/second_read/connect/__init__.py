from __future__ import annotations

import json
import logging

from second_read.config import Settings
from second_read.db import Claim, Relationship, get_session
from second_read.llm.base import LLMProvider
from second_read.prompts import CONNECT_SCHEMA, CONNECT_SYSTEM

logger = logging.getLogger(__name__)

TYPE_MIN_STRENGTH = {
    "contradicts": 0.55,
    "answers": 0.55,
    "extends": 0.5,
    "related": 0.75,  # high bar — similarity ≠ relationship
}


def label_pair(
    llm: LLMProvider,
    settings: Settings,
    claim_a: Claim,
    claim_b: Claim,
) -> Relationship | None:
    prompt = (
        f"Claim A (from \"{claim_a.item.title}\"):\n{claim_a.text}\n\n"
        f"Claim B (from \"{claim_b.item.title}\"):\n{claim_b.text}\n\n"
        "Is there a genuine claim-level relationship? "
        "If only topical similarity, set type to null."
    )
    raw = llm.complete(
        prompt,
        model=settings.model_connect,
        system=CONNECT_SYSTEM,
        schema=CONNECT_SCHEMA,
        temperature=0.2,
    )
    data = json.loads(raw)
    rel_type = data.get("type")
    if rel_type == "none" or rel_type not in TYPE_MIN_STRENGTH:
        return None
    strength = float(data.get("strength") or 0)
    rationale = (data.get("rationale") or "").strip()
    if not rationale or strength < TYPE_MIN_STRENGTH[rel_type]:
        return None

    return Relationship(
        claim_a_id=claim_a.id,
        claim_b_id=claim_b.id,
        type=rel_type,
        strength=strength,
        rationale=rationale,
    )


def connect_new_claims(
    new_claim_ids: list[int],
    llm: LLMProvider,
    settings: Settings,
) -> list[Relationship]:
    from second_read.connect.candidates import find_candidates

    pairs = find_candidates(new_claim_ids)
    if not pairs:
        return []

    session = get_session()
    created: list[Relationship] = []
    try:
        for a_id, b_id, _sim in pairs:
            # Skip if already linked either direction
            existing = (
                session.query(Relationship)
                .filter(
                    (
                        (Relationship.claim_a_id == a_id)
                        & (Relationship.claim_b_id == b_id)
                    )
                    | (
                        (Relationship.claim_a_id == b_id)
                        & (Relationship.claim_b_id == a_id)
                    )
                )
                .first()
            )
            if existing:
                continue

            claim_a = session.get(Claim, a_id)
            claim_b = session.get(Claim, b_id)
            if not claim_a or not claim_b:
                continue
            # Ensure item titles loaded
            _ = claim_a.item.title
            _ = claim_b.item.title

            try:
                rel = label_pair(llm, settings, claim_a, claim_b)
            except Exception:
                logger.exception("Failed to label claims %s ↔ %s", a_id, b_id)
                continue
            if rel is None:
                continue
            session.add(rel)
            created.append(rel)

        session.commit()
        for rel in created:
            session.refresh(rel)
        return created
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

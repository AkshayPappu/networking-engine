"""Deterministic post-filters: hedge-word drop + generic anchor-group checks."""

from __future__ import annotations

import re
from collections.abc import Iterable

from networking_engine.grounding import _normalize_url
from networking_engine.models import AnchorGroup, FetchedDocument, RankedPerson

_HEDGE_RE = re.compile(
    r"\b(unclear|possibly|likely|maybe|uncertain|not\s+clear|probably|presumably|"
    r"appears\s+to|unknown\s+if|unclear\s+if|not\s+sure|"
    r"unconfirmed|ambiguous)\b",
    re.IGNORECASE,
)


def _person_evidence_blob(
    p: RankedPerson,
    docs: list[FetchedDocument],
) -> str:
    by_url: dict[str, FetchedDocument] = {}
    for d in docs:
        by_url[_normalize_url(d.url)] = d
        by_url[d.url.strip()] = d
    parts: list[str] = []
    for ev in p.evidence:
        parts.append(ev.quote)
        doc = by_url.get(_normalize_url(ev.url)) or by_url.get(ev.url.strip())
        if doc is not None:
            parts.append(doc.text_excerpt)
    return "\n".join(parts)


def _group_satisfied(group: AnchorGroup, blob_cf: str) -> bool:
    return any(
        v.strip().casefold() in blob_cf
        for v in group.variants
        if len(v.strip()) >= 2
    )


def _evidence_passes_groups(blob_cf: str, groups: list[AnchorGroup]) -> bool:
    return all(_group_satisfied(g, blob_cf) for g in groups)


def _is_hedged(p: RankedPerson) -> bool:
    parts: list[str] = [p.current_context_guess or ""]
    if p.why_relevant:
        parts.append(p.why_relevant[0])
    blob = " ".join(parts)
    if "?" in blob:
        return True
    return bool(_HEDGE_RE.search(blob))


def apply_strict_filters(
    people: Iterable[RankedPerson],
    docs: list[FetchedDocument],
    anchor_groups: list[AnchorGroup],
) -> list[RankedPerson]:
    """Drop hedged rows; when anchor_groups is non-empty, require every group satisfied in evidence."""
    out: list[RankedPerson] = []
    for p in people:
        if _is_hedged(p):
            continue
        if anchor_groups:
            blob_cf = _person_evidence_blob(p, docs).casefold()
            if not _evidence_passes_groups(blob_cf, anchor_groups):
                continue
        out.append(p)
    return out

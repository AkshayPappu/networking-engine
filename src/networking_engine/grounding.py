from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from networking_engine.models import EvidenceItem, FetchedDocument, RankedPerson


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def _normalize_url(url: str) -> str:
    u = url.strip()
    p = urlparse(u)
    path = p.path or ""
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((p.scheme, p.netloc.lower(), path, "", p.query, ""))


def _quote_in_text(quote: str, text: str) -> bool:
    q = _norm_ws(quote)
    if len(q) < 12:
        return q in _norm_ws(text) or q in text.casefold()
    return q in _norm_ws(text)


def build_corpus(docs: list[FetchedDocument], *, max_chars_per_doc: int = 14000) -> str:
    blocks: list[str] = []
    for d in docs:
        body = d.text_excerpt
        if len(body) > max_chars_per_doc:
            body = body[: max_chars_per_doc - 1] + "…"
        title = d.title.strip() or "(no title)"
        blocks.append(f"URL: {d.url}\nTITLE: {title}\n---\n{body}\n")
    return "\n".join(blocks)


def filter_grounded_people(
    people: list[RankedPerson],
    docs: list[FetchedDocument],
) -> list[RankedPerson]:
    by_url: dict[str, FetchedDocument] = {}
    for d in docs:
        by_url[_normalize_url(d.url)] = d
        by_url[d.url.strip()] = d

    kept: list[RankedPerson] = []
    for p in people:
        name = (p.name or "").strip()
        if not name:
            continue
        new_evidence: list[EvidenceItem] = []
        for ev in p.evidence:
            u = (ev.url or "").strip()
            if not u:
                continue
            doc = by_url.get(_normalize_url(u)) or by_url.get(u)
            if doc is None:
                continue
            if not _quote_in_text(ev.quote, doc.text_excerpt):
                continue
            new_evidence.append(EvidenceItem(url=doc.url, quote=ev.quote.strip()))
        if not new_evidence:
            continue
        kept.append(
            RankedPerson(
                name=name,
                current_context_guess=p.current_context_guess.strip(),
                why_relevant=p.why_relevant,
                evidence=new_evidence,
                outreach_angle=p.outreach_angle.strip(),
            )
        )
    return kept

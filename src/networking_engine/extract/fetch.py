import asyncio

import httpx
import trafilatura
from tenacity import retry, stop_after_attempt, wait_exponential

from networking_engine.config import Settings
from networking_engine.models import FetchedDocument


def _truncate(text: str, max_chars: int) -> str:
    t = text.strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1].rstrip() + "…"


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.3, min=0.3, max=4))
async def _fetch_one(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout_s: float,
) -> tuple[str, str | None]:
    r = await client.get(url, follow_redirects=True)
    r.raise_for_status()
    ctype = (r.headers.get("content-type") or "").lower()
    if "html" not in ctype and "text" not in ctype and ctype:
        return "", None
    return r.text, r.headers.get("content-type")


async def fetch_and_extract(
    urls: list[str],
    settings: Settings,
    *,
    max_concurrency: int = 5,
    excerpt_chars: int = 12000,
) -> list[FetchedDocument]:
    headers = {"User-Agent": settings.user_agent}
    out: list[FetchedDocument] = []
    sem = asyncio.Semaphore(max_concurrency)

    async with httpx.AsyncClient(
        headers=headers,
        timeout=httpx.Timeout(settings.http_timeout_s),
        limits=httpx.Limits(max_connections=max_concurrency, max_keepalive_connections=max_concurrency),
    ) as client:

        async def one(url: str) -> FetchedDocument | None:
            async with sem:
                try:
                    html, _ctype = await _fetch_one(client, url, timeout_s=settings.http_timeout_s)
                    if not html:
                        return None
                    meta = trafilatura.extract_metadata(html)
                    title = (meta.title if meta and meta.title else "") or ""
                    extracted = trafilatura.extract(
                        html,
                        include_comments=False,
                        include_tables=False,
                        favor_recall=True,
                    )
                    text = extracted or ""
                    text = _truncate(text, excerpt_chars)
                    if not text.strip():
                        return None
                    return FetchedDocument(url=url, title=title, text_excerpt=text)
                except Exception:
                    return None

        results = await asyncio.gather(*[one(u) for u in urls])
        for doc in results:
            if doc is not None:
                out.append(doc)
    return out

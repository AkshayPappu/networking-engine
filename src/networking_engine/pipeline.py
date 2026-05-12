from __future__ import annotations

import asyncio
from collections.abc import Sequence

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    AuthenticationError,
    RateLimitError,
)
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from networking_engine.config import Settings, get_settings
from networking_engine.extract.fetch import fetch_and_extract
from networking_engine.grounding import build_corpus, filter_grounded_people
from networking_engine.llm.openai_client import OpenAIPlannerRanker
from networking_engine.models import FetchedDocument, RankedPerson, SearchHit
from networking_engine.search.factory import get_search_provider
from networking_engine.strict_filters import apply_strict_filters


def _dedupe_urls(hits: Sequence[SearchHit]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for h in hits:
        u = h.url.strip()
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


async def _search_all(
    provider,
    queries: list[str],
    *,
    per_query: int = 8,
) -> list[SearchHit]:
    sem = asyncio.Semaphore(4)

    async def one(q: str) -> list[SearchHit]:
        async with sem:
            return await provider.search(q, max_results=per_query)

    chunks = await asyncio.gather(*[one(q) for q in queries])
    merged: list[SearchHit] = []
    for c in chunks:
        merged.extend(c)
    return merged


def _prioritize_urls(hits: list[SearchHit], max_urls: int) -> list[str]:
    """Stable de-dupe; earlier search hits rank earlier."""
    urls = _dedupe_urls(hits)
    return urls[:max_urls]


def _hits_to_snippet_docs(hits: list[SearchHit]) -> list[FetchedDocument]:
    """Convert search-result snippets into FetchedDocuments so they enter the corpus
    even when the actual page cannot be fetched (e.g. LinkedIn login walls)."""
    seen: set[str] = set()
    docs: list[FetchedDocument] = []
    for h in hits:
        text = h.snippet.strip()
        if not text or h.url in seen:
            continue
        seen.add(h.url)
        docs.append(FetchedDocument(url=h.url, title=h.title, text_excerpt=text))
    return docs


def _merge_docs(
    snippet_docs: list[FetchedDocument],
    fetched_docs: list[FetchedDocument],
) -> list[FetchedDocument]:
    """Merge snippet-based and fetched docs. When the same URL appears in both,
    keep the one with the longer text_excerpt (fetched pages usually win, but
    if the fetch returned garbage or nothing, the snippet wins)."""
    by_url: dict[str, FetchedDocument] = {}
    for d in snippet_docs:
        by_url[d.url] = d
    for d in fetched_docs:
        existing = by_url.get(d.url)
        if existing is None or len(d.text_excerpt) > len(existing.text_excerpt):
            by_url[d.url] = d
    return list(by_url.values())


async def run_pipeline(
    user_query: str,
    settings: Settings,
    *,
    dry_run: bool = False,
    console: Console | None = None,
) -> int:
    con = console or Console()
    llm = OpenAIPlannerRanker(settings)
    plan = await llm.plan(user_query)
    queries = plan.search_queries or [user_query.strip()]

    con.print(Panel(plan.interpretation or "(no interpretation)", title="Interpretation"))
    if plan.must_have:
        con.print("[bold]Must have[/bold]: " + "; ".join(plan.must_have))
    if plan.nice_to_have:
        con.print("[bold]Nice to have[/bold]: " + "; ".join(plan.nice_to_have))
    if plan.anchor_groups:
        for g in plan.anchor_groups:
            con.print(f"[bold]Anchor[/bold]: {g.label} [dim]({', '.join(g.variants)})[/dim]")
    con.print("\n[bold]Search queries[/bold]:")
    for i, q in enumerate(queries, start=1):
        con.print(f"  {i}. {q}")

    if dry_run:
        con.print("\n[dim]Dry run: skipping search and ranking.[/dim]")
        return 0

    provider = None
    try:
        try:
            provider = get_search_provider(settings)
        except ValueError as e:
            con.print(f"[red]{e}[/red]")
            return 2

        hits = await _search_all(provider, queries, per_query=8)
        snippet_docs = _hits_to_snippet_docs(hits)
        urls = _prioritize_urls(hits, settings.max_urls)
        if not urls and not snippet_docs:
            con.print("[yellow]No search results. Try different API keys or queries.[/yellow]")
            return 1

        con.print(f"\n[dim]Fetching top {len(urls)} URLs…[/dim]")
        fetched_docs: list[FetchedDocument] = await fetch_and_extract(urls, settings)
        docs = _merge_docs(snippet_docs, fetched_docs)
        con.print(
            f"[dim]Corpus: {len(snippet_docs)} snippet docs, "
            f"{len(fetched_docs)} fetched pages "
            f"({len(docs)} total after merge)[/dim]"
        )
        if not docs:
            con.print("[yellow]No readable text from search snippets or fetched pages.[/yellow]")
            return 1

        corpus = build_corpus(docs)
        people = await llm.rank(
            user_query,
            corpus=corpus,
            max_people=settings.max_people,
            plan=plan,
        )
        grounded = filter_grounded_people(people, docs)
        strict = apply_strict_filters(grounded, docs, plan.anchor_groups)

        con.print(
            f"[dim]Funnel: {len(people)} from ranker → "
            f"{len(grounded)} after grounding → "
            f"{len(strict)} after strict filters[/dim]"
        )

        if not strict:
            con.print(
                "[yellow]No people passed all filters. "
                "Try increasing MAX_URLS or refining the query.[/yellow]"
            )
            return 1

        con.print("\n[bold]Results[/bold]")
        for idx, p in enumerate(strict, start=1):
            con.print(_concise_result_line(idx, p))
        return 0
    finally:
        if provider is not None:
            aclose = getattr(provider, "aclose", None)
            if callable(aclose):
                await aclose()


def _short(s: str, n: int) -> str:
    s = s.replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _concise_result_line(
    idx: int,
    p: RankedPerson,
    *,
    max_blurb: int = 100,
    max_urls: int = 8,
) -> str:
    blurb = (p.current_context_guess or "").strip()
    if not blurb and p.why_relevant:
        blurb = str(p.why_relevant[0]).strip()
    blurb = _short(blurb, max_blurb) if blurb else "—"
    urls = list(dict.fromkeys(e.url for e in p.evidence))
    shown = urls[:max_urls]
    parts = " ".join(shown)
    if len(urls) > max_urls:
        parts += f" [dim](+{len(urls) - max_urls} more)[/dim]"
    return f"{idx}. [bold]{p.name}[/bold] — {blurb} | {parts}"


def run_query(user_query: str, *, dry_run: bool = False) -> int:
    try:
        settings = get_settings()
    except ValidationError as e:
        Console(stderr=True).print(
            "[red]Configuration error.[/red] Copy [bold].env.example[/bold] to [bold].env[/bold] "
            "and set [bold]OPENAI_API_KEY[/bold] plus your search provider key "
            "([bold]TAVILY_API_KEY[/bold] or [bold]BRAVE_API_KEY[/bold]). See README.\n"
            f"[dim]{e}[/dim]"
        )
        return 2
    err = Console(stderr=True)
    try:
        return asyncio.run(run_pipeline(user_query, settings, dry_run=dry_run))
    except RateLimitError as e:
        err.print(
            "[bold red]OpenAI returned 429 (rate limit or quota).[/bold red]\n"
            "If the message mentions [bold]insufficient_quota[/bold], add billing/credits or "
            "switch to an API key with an active plan.\n"
            "Billing: https://platform.openai.com/account/billing"
        )
        err.print(f"[dim]{e.message}[/dim]")
        return 3
    except AuthenticationError:
        err.print(
            "[bold red]OpenAI authentication failed (401).[/bold red] "
            "Check [bold]OPENAI_API_KEY[/bold] in your .env file."
        )
        return 4
    except APIConnectionError as e:
        err.print(f"[bold red]Could not connect to OpenAI.[/bold red] [dim]{e.message}[/dim]")
        return 5
    except APIStatusError as e:
        err.print(
            f"[bold red]OpenAI API error[/bold red] ({e.status_code}): [dim]{e.message}[/dim]"
        )
        return 1
    except APIError as e:
        err.print(f"[bold red]OpenAI error:[/bold red] [dim]{e.message}[/dim]")
        return 1

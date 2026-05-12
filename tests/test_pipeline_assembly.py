from networking_engine.grounding import build_corpus
from networking_engine.models import FetchedDocument, SearchHit
from networking_engine.pipeline import _hits_to_snippet_docs, _merge_docs


def test_ranker_corpus_fixture_shape() -> None:
    """Frozen-style fixture: deterministic corpus assembly for ranker input."""
    docs = [
        FetchedDocument(
            url="https://example.com/one",
            title="Post",
            text_excerpt="Dr. Pat Lee leads inference at Contoso and previously interned at VT.",
        ),
        FetchedDocument(
            url="https://example.com/two",
            title="News",
            text_excerpt="Contoso hires ML infra engineers from regional universities.",
        ),
    ]
    corpus = build_corpus(docs, max_chars_per_doc=5000)
    assert corpus.startswith("URL: https://example.com/one")
    assert "Contoso" in corpus
    assert "URL: https://example.com/two" in corpus


def test_hits_to_snippet_docs_basic() -> None:
    hits = [
        SearchHit(url="https://linkedin.com/in/alice", title="Alice", snippet="Alice - SWE at DRW, ex-Google"),
        SearchHit(url="https://linkedin.com/in/bob", title="Bob", snippet="Bob - Trader at Citadel"),
        SearchHit(url="https://example.com/empty", title="Empty", snippet=""),
    ]
    docs = _hits_to_snippet_docs(hits)
    assert len(docs) == 2
    assert docs[0].url == "https://linkedin.com/in/alice"
    assert "DRW" in docs[0].text_excerpt
    assert docs[1].url == "https://linkedin.com/in/bob"


def test_hits_to_snippet_docs_dedupes_urls() -> None:
    hits = [
        SearchHit(url="https://linkedin.com/in/alice", title="Alice", snippet="First snippet"),
        SearchHit(url="https://linkedin.com/in/alice", title="Alice", snippet="Second snippet"),
    ]
    docs = _hits_to_snippet_docs(hits)
    assert len(docs) == 1
    assert docs[0].text_excerpt == "First snippet"


def test_merge_docs_prefers_longer_text() -> None:
    snippet_docs = [
        FetchedDocument(url="https://example.com/a", title="A", text_excerpt="Short snippet."),
    ]
    fetched_docs = [
        FetchedDocument(url="https://example.com/a", title="A Full", text_excerpt="Much longer fetched page text with details."),
    ]
    merged = _merge_docs(snippet_docs, fetched_docs)
    assert len(merged) == 1
    assert "Much longer" in merged[0].text_excerpt


def test_merge_docs_keeps_snippet_when_no_fetch() -> None:
    snippet_docs = [
        FetchedDocument(url="https://linkedin.com/in/alice", title="Alice", text_excerpt="Alice - SWE at DRW"),
    ]
    fetched_docs = []
    merged = _merge_docs(snippet_docs, fetched_docs)
    assert len(merged) == 1
    assert merged[0].url == "https://linkedin.com/in/alice"


def test_merge_docs_combines_different_urls() -> None:
    snippet_docs = [
        FetchedDocument(url="https://linkedin.com/in/alice", title="Alice", text_excerpt="Alice snippet"),
    ]
    fetched_docs = [
        FetchedDocument(url="https://example.com/page", title="Page", text_excerpt="Fetched page text"),
    ]
    merged = _merge_docs(snippet_docs, fetched_docs)
    assert len(merged) == 2
    urls = {d.url for d in merged}
    assert "https://linkedin.com/in/alice" in urls
    assert "https://example.com/page" in urls


def test_merge_docs_snippet_wins_when_fetch_shorter() -> None:
    snippet_docs = [
        FetchedDocument(url="https://example.com/a", title="A", text_excerpt="A very detailed search snippet with lots of info."),
    ]
    fetched_docs = [
        FetchedDocument(url="https://example.com/a", title="A", text_excerpt="Tiny."),
    ]
    merged = _merge_docs(snippet_docs, fetched_docs)
    assert len(merged) == 1
    assert "detailed search snippet" in merged[0].text_excerpt

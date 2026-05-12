import pytest

from networking_engine.grounding import build_corpus, filter_grounded_people
from networking_engine.models import EvidenceItem, FetchedDocument, RankedPerson, SearchHit


def test_search_hit_rejects_non_http_url() -> None:
    with pytest.raises(ValueError):
        SearchHit(url="ftp://x.com", title="", snippet="")


def test_build_corpus_includes_urls() -> None:
    docs = [
        FetchedDocument(url="https://a.example/x", title="T", text_excerpt="Alice Smith works at Acme."),
    ]
    c = build_corpus(docs)
    assert "https://a.example/x" in c
    assert "Alice Smith" in c


def test_filter_grounded_keeps_matching_quote() -> None:
    docs = [
        FetchedDocument(
            url="https://a.example/p",
            title="Bio",
            text_excerpt="Jane Doe is a software engineer at OpenAI based in SF.",
        )
    ]
    people = [
        RankedPerson(
            name="Jane Doe",
            current_context_guess="Engineer at OpenAI",
            why_relevant=["Mentioned as engineer at OpenAI."],
            evidence=[
                EvidenceItem(
                    url="https://a.example/p",
                    quote="Jane Doe is a software engineer at OpenAI",
                )
            ],
            outreach_angle="Mention you saw her role at OpenAI on the public bio page.",
        )
    ]
    out = filter_grounded_people(people, docs)
    assert len(out) == 1
    assert out[0].name == "Jane Doe"


def test_filter_grounded_drops_bad_quote() -> None:
    docs = [
        FetchedDocument(
            url="https://a.example/p",
            title="Bio",
            text_excerpt="Totally different text without the claimed quote.",
        )
    ]
    people = [
        RankedPerson(
            name="Nobody",
            why_relevant=["x"],
            evidence=[EvidenceItem(url="https://a.example/p", quote="This quote is not in the page.")],
        )
    ]
    assert filter_grounded_people(people, docs) == []


def test_filter_grounded_drops_unknown_url() -> None:
    docs = [FetchedDocument(url="https://a.example/p", text_excerpt="hello")]
    people = [
        RankedPerson(
            name="X",
            evidence=[EvidenceItem(url="https://other.example/", quote="hello")],
        )
    ]
    assert filter_grounded_people(people, docs) == []

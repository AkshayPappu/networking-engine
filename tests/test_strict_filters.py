from networking_engine.models import AnchorGroup, EvidenceItem, FetchedDocument, RankedPerson
from networking_engine.strict_filters import apply_strict_filters


def _person(
    name: str,
    *,
    guess: str,
    why: list[str],
    quote: str,
    url: str = "https://ex.com/p",
) -> RankedPerson:
    return RankedPerson(
        name=name,
        current_context_guess=guess,
        why_relevant=why,
        evidence=[EvidenceItem(url=url, quote=quote)],
        outreach_angle="",
    )


def test_all_groups_satisfied_passes() -> None:
    docs = [FetchedDocument(url="https://ex.com/p", text_excerpt="Former Acme Corp engineer, now at Initech.")]
    groups = [
        AnchorGroup(label="Previously at Acme Corp", variants=["Acme Corp", "Acme"]),
        AnchorGroup(label="Currently at Initech", variants=["Initech"]),
    ]
    p = _person("Pat", guess="Initech engineer ex-Acme", why=["Both"], quote="Former Acme Corp engineer, now at Initech.")
    assert len(apply_strict_filters([p], docs, groups)) == 1


def test_one_group_missing_drops() -> None:
    docs = [FetchedDocument(url="https://ex.com/p", text_excerpt="Works at Initech.")]
    groups = [
        AnchorGroup(label="Previously at Acme Corp", variants=["Acme Corp", "Acme"]),
        AnchorGroup(label="Currently at Initech", variants=["Initech"]),
    ]
    p = _person("Sam", guess="Initech only", why=["x"], quote="Works at Initech.")
    assert apply_strict_filters([p], docs, groups) == []


def test_variant_alias_match() -> None:
    docs = [FetchedDocument(url="https://ex.com/p", text_excerpt="Worked at JS; previously at GOOG.")]
    groups = [
        AnchorGroup(label="Previously at Google", variants=["Google", "GOOG", "Alphabet"]),
        AnchorGroup(label="Currently at Jane Street", variants=["Jane Street", "JS"]),
    ]
    p = _person("Alex", guess="JS trader ex-Google", why=["Both"], quote="Worked at JS; previously at GOOG.")
    assert len(apply_strict_filters([p], docs, groups)) == 1


def test_hedge_question_mark_drops() -> None:
    docs = [FetchedDocument(url="https://ex.com/p", text_excerpt="Some text.")]
    p = _person("Jane", guess="Acme? unclear", why=["x"], quote="Some text.")
    assert apply_strict_filters([p], docs, []) == []


def test_hedge_word_drops() -> None:
    docs = [FetchedDocument(url="https://ex.com/p", text_excerpt="Some text.")]
    p = _person("Bob", guess="Possibly at Acme", why=["y"], quote="Some text.")
    assert apply_strict_filters([p], docs, []) == []


def test_empty_groups_skips_anchor_filter() -> None:
    docs = [FetchedDocument(url="https://ex.com/p", text_excerpt="x")]
    p = _person("Z", guess="Clear statement", why=["ok"], quote="x")
    assert len(apply_strict_filters([p], docs, [])) == 1


def test_empty_groups_still_drops_hedged() -> None:
    docs = [FetchedDocument(url="https://ex.com/p", text_excerpt="x")]
    p = _person("Z2", guess="unclear", why=["ok"], quote="x")
    assert apply_strict_filters([p], docs, []) == []


def test_case_insensitive_variant_match() -> None:
    docs = [FetchedDocument(url="https://ex.com/p", text_excerpt="engineer at MEGACORP")]
    groups = [AnchorGroup(label="At MegaCorp", variants=["MegaCorp", "megacorp"])]
    p = _person("Lee", guess="MegaCorp engineer", why=["Bio"], quote="engineer at MEGACORP")
    assert len(apply_strict_filters([p], docs, groups)) == 1

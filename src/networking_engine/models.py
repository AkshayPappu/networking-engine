from pydantic import BaseModel, Field, field_validator


class EvidenceItem(BaseModel):
    url: str
    quote: str = Field(..., max_length=2000)


class RankedPerson(BaseModel):
    name: str
    current_context_guess: str = ""
    why_relevant: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    outreach_angle: str = ""

    @field_validator("why_relevant", mode="before")
    @classmethod
    def _coerce_why(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return []


class RankerResponse(BaseModel):
    people: list[RankedPerson] = Field(default_factory=list)


class AnchorGroup(BaseModel):
    """One required concept (e.g. an employer) with all known aliases.
    All groups are ANDed; variants within a group are ORed."""
    label: str = Field(..., description="Human-readable, e.g. 'Currently at Hudson River Trading'")
    variants: list[str] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="Substrings — any one match in evidence satisfies this group.",
    )


class PlannerOutput(BaseModel):
    interpretation: str = ""
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list, max_length=12)
    negative_signals: list[str] = Field(default_factory=list)
    anchor_groups: list[AnchorGroup] = Field(
        default_factory=list,
        description="1-4 required concept groups. Each group has variants (OR). All groups are AND.",
    )

    @field_validator("search_queries", mode="before")
    @classmethod
    def _normalize_queries(cls, v: object) -> list[str]:
        if not isinstance(v, list):
            return []
        out: list[str] = []
        for q in v:
            s = str(q).strip()
            if s and s not in out:
                out.append(s)
        return out[:12]


class SearchHit(BaseModel):
    title: str = ""
    url: str
    snippet: str = ""

    @field_validator("url")
    @classmethod
    def _strip_url(cls, v: str) -> str:
        s = str(v).strip()
        if not (s.startswith("http://") or s.startswith("https://")):
            raise ValueError("url must be http(s)")
        return s


class FetchedDocument(BaseModel):
    url: str
    title: str = ""
    text_excerpt: str = ""

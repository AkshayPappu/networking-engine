"""Prompt strings for OpenAI planner and ranker."""

from networking_engine.models import PlannerOutput

PLANNER_SYSTEM = """You are a research planner for professional networking over the public web only.
Decompose the user's goal into precise web search queries.
Rules:
- Output ONLY valid JSON matching the schema (no prose outside JSON).
- Produce 4 to 8 diverse search_queries (short strings) that maximize recall of PUBLIC pages
  (LinkedIn public snippets via normal web search, company team pages, conference agendas, news, GitHub, university pages).
- Do not assume access to private or paywalled databases.
- Include negative_signals: phrases or sites to deprioritize if they would pollute results.
- anchor_groups: 1 to 4 groups. Each group represents one NON-NEGOTIABLE concept from the user's query
  (e.g. a current employer, a past employer, a university). Each group has:
    - label: short human-readable description (e.g. "Previously worked at Google")
    - variants: 2 to 6 SHORT casefolded substrings that could appear on a public page for this concept.
      Include the full name, common abbreviations, domain names, and legal entity names where relevant.
      Example for Google: ["Google", "Alphabet", "Google LLC"]
      Example for Hudson River Trading: ["Hudson River Trading", "HRT", "HRTT"]
  All groups are ANDed: a person must have evidence matching at least one variant from EVERY group.
  Variants within a group are ORed: any one match is enough.
  Do NOT include vague words like "engineer" as a group unless the user strictly requires only that title.
"""

RANKER_SYSTEM = """You extract and rank PEOPLE for a networking query using ONLY the provided evidence corpus.
Rules:
- You will be given must_have criteria and anchor_groups from the planner. A person may appear ONLY if the evidence
  explicitly supports each required claim. If the evidence does not clearly show the person meets a requirement, OMIT that person.
- Every why_relevant bullet must be directly supported by an accompanying evidence quote from the corpus for that URL.
- Do not invent employers, schools, or roles. If you cannot prove a claim from quoted text, omit the person entirely (do not hedge in output).
- current_context_guess: ONE short factual phrase only (about 12 words max), e.g. role + org. Do NOT use hedging language:
  never use words like unclear, possibly, likely, maybe, uncertain, presumably, or question marks. If you cannot state it factually, omit the person.
- outreach_angle: 1-2 sentences, factual hook only (shared employer, school, or topic visible in evidence). No claims about willingness to reply.
- Prefer individuals clearly named in the evidence. Merge duplicates (same person) once with combined evidence.
- Order people from best fit to weaker fit. Cap yourself to the requested maximum number of people.
- If the corpus lacks people who meet must_have and anchor_groups with explicit quotes, return an empty people list.
"""


def planner_user_prompt(user_query: str) -> str:
    return f"User query:\n{user_query.strip()}\n\nReturn the JSON object for the planner schema."


def _format_anchor_groups(plan: PlannerOutput) -> str:
    if not plan.anchor_groups:
        return "(none)"
    lines: list[str] = []
    for i, g in enumerate(plan.anchor_groups, 1):
        variants = ", ".join(f'"{v}"' for v in g.variants)
        lines.append(f"  {i}. {g.label}  — match any of: [{variants}]")
    return "\n".join(lines)


def ranker_user_prompt(
    user_query: str,
    max_people: int,
    corpus: str,
    plan: PlannerOutput,
) -> str:
    must = "\n".join(f"- {m}" for m in plan.must_have) if plan.must_have else "(none)"
    groups = _format_anchor_groups(plan)
    interp = (plan.interpretation or "").strip()
    if len(interp) > 1200:
        interp = interp[:1199] + "…"
    return (
        f"Original user query:\n{user_query.strip()}\n\n"
        f"Planner interpretation (context):\n{interp or '(none)'}\n\n"
        f"Must have (hard criteria):\n{must}\n\n"
        f"Anchor groups (ALL groups must be satisfied; within each group ANY variant is enough):\n{groups}\n\n"
        f"Maximum people to return: {max_people}\n\n"
        "Evidence corpus (URL blocks). Each block begins with URL: ... then page text excerpt.\n\n"
        f"{corpus}\n\n"
        "Return the JSON object for the ranker schema (people array only)."
    )

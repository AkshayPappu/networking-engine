from openai import AsyncOpenAI

from networking_engine.config import Settings
from networking_engine.llm import prompts
from networking_engine.models import PlannerOutput, RankedPerson, RankerResponse


class OpenAIPlannerRanker:
    def __init__(self, settings: Settings) -> None:
        self._model = settings.openai_model
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def plan(self, user_query: str) -> PlannerOutput:
        resp = await self._client.chat.completions.parse(
            model=self._model,
            messages=[
                {"role": "system", "content": prompts.PLANNER_SYSTEM},
                {"role": "user", "content": prompts.planner_user_prompt(user_query)},
            ],
            response_format=PlannerOutput,
        )
        choice = resp.choices[0].message
        parsed = choice.parsed
        if parsed is None:
            raise RuntimeError("Planner returned no structured output")
        return parsed

    async def rank(
        self,
        user_query: str,
        *,
        corpus: str,
        max_people: int,
        plan: PlannerOutput,
    ) -> list[RankedPerson]:
        resp = await self._client.chat.completions.parse(
            model=self._model,
            messages=[
                {"role": "system", "content": prompts.RANKER_SYSTEM},
                {
                    "role": "user",
                    "content": prompts.ranker_user_prompt(user_query, max_people, corpus, plan),
                },
            ],
            response_format=RankerResponse,
        )
        choice = resp.choices[0].message
        parsed = choice.parsed
        if parsed is None:
            raise RuntimeError("Ranker returned no structured output")
        return list(parsed.people)[:max_people]

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from networking_engine.models import SearchHit


class TavilySearch:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(base_url="https://api.tavily.com", timeout=30.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=8))
    async def search(self, query: str, *, max_results: int = 8) -> list[SearchHit]:
        payload = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": False,
            "max_results": max_results,
        }
        r = await self._client.post("/search", json=payload)
        r.raise_for_status()
        data = r.json()
        hits: list[SearchHit] = []
        for row in data.get("results") or []:
            url = (row.get("url") or "").strip()
            if not url:
                continue
            try:
                hits.append(
                    SearchHit(
                        title=str(row.get("title") or ""),
                        url=url,
                        snippet=str(row.get("content") or row.get("snippet") or ""),
                    )
                )
            except Exception:
                continue
        return hits

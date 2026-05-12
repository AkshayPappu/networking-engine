import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from networking_engine.models import SearchHit


class BraveSearch:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url="https://api.search.brave.com/res/v1",
            headers={"X-Subscription-Token": api_key},
            timeout=30.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=8))
    async def search(self, query: str, *, max_results: int = 8) -> list[SearchHit]:
        r = await self._client.get(
            "/web/search",
            params={"q": query, "count": max_results},
        )
        r.raise_for_status()
        data = r.json()
        hits: list[SearchHit] = []
        web = data.get("web") or {}
        for row in web.get("results") or []:
            url = (row.get("url") or "").strip()
            if not url:
                continue
            desc = row.get("description") or row.get("title") or ""
            try:
                hits.append(
                    SearchHit(
                        title=str(row.get("title") or ""),
                        url=url,
                        snippet=str(desc),
                    )
                )
            except Exception:
                continue
        return hits

from typing import Protocol

from networking_engine.models import SearchHit


class SearchProvider(Protocol):
    async def search(self, query: str, *, max_results: int = 8) -> list[SearchHit]: ...

from networking_engine.config import Settings
from networking_engine.search.brave import BraveSearch
from networking_engine.search.protocol import SearchProvider
from networking_engine.search.tavily import TavilySearch


def get_search_provider(settings: Settings) -> SearchProvider:
    if settings.search_provider == "tavily":
        if not settings.tavily_api_key:
            raise ValueError("TAVILY_API_KEY is required when SEARCH_PROVIDER=tavily")
        return TavilySearch(settings.tavily_api_key)
    if not settings.brave_api_key:
        raise ValueError("BRAVE_API_KEY is required when SEARCH_PROVIDER=brave")
    return BraveSearch(settings.brave_api_key)

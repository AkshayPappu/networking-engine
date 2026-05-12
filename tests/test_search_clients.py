import httpx
import pytest
import respx

from networking_engine.search.tavily import TavilySearch


@pytest.mark.asyncio
async def test_tavily_search_parses_results() -> None:
    payload = {
        "results": [
            {
                "url": "https://example.com/a",
                "title": "Title A",
                "content": "Snippet A",
            }
        ]
    }
    with respx.mock:
        respx.post("https://api.tavily.com/search").mock(
            return_value=httpx.Response(200, json=payload)
        )
        client = TavilySearch("test-key")
        try:
            hits = await client.search("machine learning hiring", max_results=5)
        finally:
            await client.aclose()
    assert len(hits) == 1
    assert hits[0].url == "https://example.com/a"
    assert hits[0].title == "Title A"


@pytest.mark.asyncio
async def test_brave_search_parses_results() -> None:
    from networking_engine.search.brave import BraveSearch

    body = {
        "web": {
            "results": [
                {"url": "https://openai.com/team", "title": "Team", "description": "People at OpenAI"}
            ]
        }
    }
    with respx.mock:
        respx.get(url__regex=r"https://api\.search\.brave\.com/res/v1/web/search.*").mock(
            return_value=httpx.Response(200, json=body)
        )
        b = BraveSearch("brave-key")
        try:
            hits = await b.search("OpenAI team page", max_results=3)
        finally:
            await b.aclose()
    assert len(hits) == 1
    assert "openai.com" in hits[0].url

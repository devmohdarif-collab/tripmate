import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

client = TavilyClient(os.getenv("TAVILY_API_KEY"))


def tavily_search(query: str, search_depth: str = "basic"):
    response = client.search(
        query=query,
        search_depth=search_depth
    )
    return response


def format_results(response):
    results = []

    for i, r in enumerate(response["results"], start=1):
        title = r.get("title", "No title available")
        url = r.get("url", "No URL available")
        snippet = r.get("content", "No content available").strip()

        if len(snippet) > 300:
            snippet = snippet[:300] + "..."

        results.append(
            f"{i}. **{title}**\n{url}\n{snippet}"
        )

    return "\n\n".join(results)

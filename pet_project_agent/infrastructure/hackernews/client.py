import requests

from pet_project_agent.domain.models import HackerNewsItem


class HackerNewsClient:
    BASE_URL = "https://hn.algolia.com/api/v1/search"

    def search(self, query: str, limit: int = 5) -> list[HackerNewsItem]:
        params = {
            "query": query,
            "hitsPerPage": limit,
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
        except requests.RequestException as error:
            raise RuntimeError(f"Hacker News API request failed: {error}") from error

        data = response.json()
        items: list[HackerNewsItem] = []

        for hit in data.get("hits", []):
            title = (hit.get("title") or hit.get("story_title") or "").strip()

            if not title:
                continue

            items.append(
                HackerNewsItem(
                    title=title,
                    url=hit.get("url") or hit.get("story_url"),
                    points=hit.get("points") or 0,
                    author=hit.get("author") or "unknown",
                    created_at=hit.get("created_at") or "",
                )
            )

        return items

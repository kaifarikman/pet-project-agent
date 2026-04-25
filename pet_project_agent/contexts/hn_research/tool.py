from pet_project_agent.domain.models import HackerNewsItem
from pet_project_agent.infrastructure.hackernews.client import HackerNewsClient


class HackerNewsSearchTool:
    name = "hackernews_search_tool"

    def __init__(self, client: HackerNewsClient, limit: int = 5) -> None:
        self.client = client
        self.limit = limit

    def run(self, query: str) -> list[HackerNewsItem]:
        return self.client.search(query=query, limit=self.limit)

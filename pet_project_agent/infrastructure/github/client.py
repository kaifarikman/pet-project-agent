import os

import requests

from pet_project_agent.domain.models import GitHubRepository


class GitHubClient:
    BASE_URL = "https://api.github.com/search/repositories"

    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")

    def search_repositories(
            self,
            query: str,
            limit: int = 3,
            min_stars: int = 5,
    ) -> list[GitHubRepository]:
        params = {
            "q": f"{query} stars:>={min_stars} archived:false",
            "sort": "stars",
            "order": "desc",
            "per_page": limit,
        }

        headers = {
            "Accept": "application/vnd.github+json",
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        response = requests.get(
            self.BASE_URL,
            params=params,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        repositories: list[GitHubRepository] = []

        for item in data.get("items", []):
            repositories.append(
                GitHubRepository(
                    name=item["full_name"],
                    url=item["html_url"],
                    description=item.get("description"),
                    language=item.get("language"),
                    stars=item.get("stargazers_count", 0),
                    topics=item.get("topics", []),
                )
            )

        return repositories

import os
import logging
import requests
from typing import List, Optional

from pet_project_agent.domain.models import GitHubRepository

logger = logging.getLogger(__name__)

class GitHubClient:
    BASE_URL = "https://api.github.com/search/repositories"

    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")

    def search_repositories(
        self,
        query: str,
        limit: int = 5,
        min_stars: int = 0,
    ) -> List[GitHubRepository]:
        # Формируем безопасный запрос
        # Убираем двойные пробелы и спецсимволы, которые могут сломать синтаксис GitHub Search
        clean_query = " ".join(query.split())
        search_query = f"{clean_query} stars:>={min_stars} archived:false fork:false"
        
        params = {
            "q": search_query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(limit, 100), # GitHub не дает больше 100 за раз
        }

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pet-project-agent-cli" # GitHub просит указывать User-Agent
        }

        if self.token:
            headers["Authorization"] = f"token {self.token}"

        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=15,
            )
            
            # Обработка лимитов запросов
            if response.status_code == 403:
                logger.warning("GitHub API rate limit exceeded or access forbidden.")
                return []
                
            response.raise_for_status()
            
        except requests.RequestException as error:
            logger.error(f"GitHub API request failed for query '{search_query}': {error}")
            # Возвращаем пустой список вместо падения, чтобы агент мог продолжить работу на данных LLM
            return []

        data = response.json()
        repositories: List[GitHubRepository] = []

        for item in data.get("items", []):
            try:
                repositories.append(
                    GitHubRepository(
                        name=item["full_name"],
                        url=item["html_url"],
                        description=item.get("description") or "",
                        language=item.get("language") or "Unknown",
                        stars=item.get("stargazers_count", 0),
                        topics=item.get("topics") or [],
                    )
                )
            except KeyError as e:
                logger.warning(f"Skipping repository due to missing key {e}")
                continue

        return repositories

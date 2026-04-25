import json
import logging
from typing import List

from pet_project_agent.domain.models import GitHubResearchData
from pet_project_agent.domain.models import GitHubRepository
from pet_project_agent.domain.models import Skill
from pet_project_agent.domain.models import UserProfile
from pet_project_agent.domain.ports import LLMClientPort
from pet_project_agent.contexts.profile.service import ProfileService
from pet_project_agent.infrastructure.data.skill_catalog_repository import SkillCatalogRepository
from pet_project_agent.infrastructure.github.client import GitHubClient

logger = logging.getLogger(__name__)

class GitHubSearchTool:
    name = "github_search_tool"
    
    def __init__(
        self,
        client: GitHubClient,
        limit: int = 5,
        min_stars: int = 0,
        skill_catalog_repository: SkillCatalogRepository | None = None,
        profile_service: ProfileService | None = None,
        llm_client: LLMClientPort | None = None,
    ) -> None:
        self.client = client
        self.limit = limit
        self.min_stars = min_stars
        self.skill_catalog_repository = skill_catalog_repository
        self.profile_service = profile_service or ProfileService()
        self.llm_client = llm_client
        self.skills_catalog = self._load_skills_catalog()

    def run(self, query: str, user_profile: UserProfile | None = None) -> GitHubResearchData:
        profile = user_profile or self._build_profile(query)
        
        # Умное расширение запросов через LLM
        search_queries = self._build_search_queries(query, profile)
        
        repositories_by_url: dict[str, GitHubRepository] = {}

        for search_query in search_queries:
            try:
                repositories = self.client.search_repositories(
                    query=search_query,
                    limit=self.limit,
                    min_stars=self.min_stars,
                )
                for repository in repositories:
                    repositories_by_url.setdefault(repository.url, repository)
            except Exception as e:
                logger.warning(f"Search failed for query '{search_query}': {e}")
                continue

        ranked_repositories = self._rank_repositories(
            repositories=list(repositories_by_url.values()),
            raw_query=query,
            profile=profile,
        )[: self.limit]
        
        return GitHubResearchData(
            search_queries=search_queries,
            repositories=ranked_repositories,
            patterns=[], # Паттерны теперь менее важны при наличии LLM ideation
        )

    def _load_skills_catalog(self) -> list[Skill]:
        if self.skill_catalog_repository is None: return []
        return self.skill_catalog_repository.load_skills()

    def _build_profile(self, query: str) -> UserProfile:
        if not self.skills_catalog: return UserProfile(raw_text=query)
        return self.profile_service.build_profile(query, self.skills_catalog)

    def _build_search_queries(self, raw_query: str, profile: UserProfile) -> List[str]:
        if self.llm_client is None:
            # Твердый fallback, если LLM недоступна
            lang = profile.skills[0] if profile.skills else "software"
            return [f"{lang} project", f"{lang} starter"]

        prompt = f"""
Вы — эксперт по поиску на GitHub. Сгенерируйте 3-5 поисковых запросов на АНГЛИЙСКОМ языке, чтобы найти простые проекты для портфолио.

Контекст пользователя: "{raw_query}"
Язык/Навыки: {', '.join(profile.skills) if profile.skills else "JavaScript"}

Правила:
1. ВСЕГДА генерируйте запросы на АНГЛИЙСКОМ языке (так как GitHub лучше ищет на английском).
2. Если пользователь новичок или хочет что-то простое, используйте термины: "vanilla", "beginner-friendly", "simple-project", "coding-exercises".
3. Избегайте слишком общих терминов, таких как просто "javascript". Используйте "javascript-projects" или "js-app".
4. Верните ТОЛЬКО JSON-массив строк.

Пример: ["vanilla javascript projects for beginners", "simple js calculator tutorial", "beginner friendly web apps"]
""".strip()

        try:
            raw_response = self.llm_client.generate(prompt, json_mode=True)
            queries = json.loads(raw_response)
            if isinstance(queries, list):
                return [str(q) for q in queries[:5]]
            if isinstance(queries, dict) and "queries" in queries:
                return [str(q) for q in queries["queries"][:5]]
        except Exception as e:
            logger.error(f"Failed to expand search queries via LLM: {e}")
            
        # Fallback на случай ошибки LLM
        return [f"{s} project" for s in profile.skills[:2]] or ["awesome pet projects"]

    def _rank_repositories(self, repositories: list[GitHubRepository], raw_query: str, profile: UserProfile) -> list[GitHubRepository]:
        scored = []
        
        for repo in repositories:
            score = 10.0 # Базовый балл
            text = f"{repo.name} {repo.description} {' '.join(repo.topics)}".lower()
            
            # 1. ШТРАФ ЗА ГИГАНТОМАНИЮ (анти-AWX фильтр)
            # Если звезд > 10000, это скорее всего не пет-проект, а огромная платформа
            if repo.stars > 10000:
                score -= 30.0
            elif repo.stars > 5000:
                score -= 15.0
                
            # Штраф за корпоративные слова
            enterprise_words = ["enterprise", "platform", "infrastructure", "official", "managed"]
            if any(w in text for w in enterprise_words):
                score -= 10.0

            # 2. Соответствие навыкам из профиля
            for skill in profile.skills:
                if skill.lower() in text: 
                    score += 7.0 # Увеличили бонус за стек
            
            # 3. Бонус за популярность (но умеренный, чтобы не вызывать перекос)
            # Теперь звезды дают максимум +5 баллов
            score += min(repo.stars / 2000, 5)
            
            scored.append((repo, score))
            
        scored.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in scored]

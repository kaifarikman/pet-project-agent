from pet_project_agent.domain.models import GitHubResearchData
from pet_project_agent.domain.models import GitHubRepository
from pet_project_agent.domain.models import RepositoryPattern
from pet_project_agent.domain.models import Skill
from pet_project_agent.domain.models import UserProfile
from pet_project_agent.contexts.profile.service import ProfileService
from pet_project_agent.infrastructure.data.skill_catalog_repository import SkillCatalogRepository
from pet_project_agent.infrastructure.github.client import GitHubClient


class GitHubSearchTool:
    name = "github_search_tool"
    
    PATTERN_RULES = {
        "api_service": {
            "required": ["api", "rest", "backend", "service", "server"],
            "optional": ["crud", "fastapi", "django", "flask", "endpoint"],
            "negative": ["dashboard", "analytics", "telegram", "discord", "bot", "ml", "security"],
            "threshold": 3.0,
        },
        "dashboard": {
            "required": ["dashboard", "analytics", "visualization", "charts", "metrics"],
            "optional": ["insights", "report", "bi", "pandas", "sql"],
            "negative": ["telegram", "discord", "bot", "scanner", "vulnerability"],
            "threshold": 3.0,
        },
        "bot": {
            "required": ["bot", "telegram", "discord", "chat"],
            "optional": ["reminder", "assistant", "automation", "ai"],
            "negative": ["dashboard", "analytics", "scanner", "vulnerability"],
            "threshold": 3.0,
        },
        "ml_app": {
            "required": ["machine learning", "predict", "classification", "regression", "inference", "ai"],
            "optional": ["ml", "model", "dataset", "training", "ollama"],
            "negative": ["crud", "kanban"],
            "threshold": 3.0,
        },
    }

    STOP_TERMS = {
        "portfolio", "портфолио", "week", "weeks", "month", "months", "day", "days",
        "хочу", "найди", "реальные", "open-source", "opensource", "примеры", "example", "examples",
        "project", "проект"
    }

    def __init__(
        self,
        client: GitHubClient,
        limit: int = 5,
        min_stars: int = 0,
        skill_catalog_repository: SkillCatalogRepository | None = None,
        profile_service: ProfileService | None = None,
    ) -> None:
        self.client = client
        self.limit = limit
        self.min_stars = min_stars
        self.skill_catalog_repository = skill_catalog_repository
        self.profile_service = profile_service or ProfileService()
        self.skills_catalog = self._load_skills_catalog()

    def run(self, query: str, user_profile: UserProfile | None = None) -> GitHubResearchData:
        profile = user_profile or self._build_profile(query)
        search_queries = self._build_search_queries(query, profile)
        repositories_by_url: dict[str, GitHubRepository] = {}

        for search_query in search_queries:
            repositories = self.client.search_repositories(
                query=search_query,
                limit=self.limit,
                min_stars=self.min_stars,
            )
            for repository in repositories:
                repositories_by_url.setdefault(repository.url, repository)

        ranked_repositories = self._rank_repositories(
            repositories=list(repositories_by_url.values()),
            raw_query=query,
            profile=profile,
        )[: self.limit]
        
        return GitHubResearchData(
            search_queries=search_queries,
            repositories=ranked_repositories,
            patterns=self._build_patterns(ranked_repositories),
        )

    def _load_skills_catalog(self) -> list[Skill]:
        if self.skill_catalog_repository is None: return []
        return self.skill_catalog_repository.load_skills()

    def _build_profile(self, query: str) -> UserProfile:
        if not self.skills_catalog: return UserProfile(raw_text=query)
        return self.profile_service.build_profile(query, self.skills_catalog)

    def _build_search_queries(self, raw_query: str, profile: UserProfile) -> list[str]:
        queries: list[str] = []
        tokens = self._extract_query_tokens(raw_query)
        
        # Определяем язык программирования
        lang = None
        for skill in profile.skills:
            if skill in ["python", "javascript", "typescript", "java", "go", "cpp", "csharp"]:
                lang = skill
                break

        # 1. Точный запрос по токенам
        if tokens:
            base = " ".join(tokens[:3])
            queries.append(f"{base} {f'language:{lang}' if lang else ''}".strip())
            # 2. Тот же запрос + слово project
            queries.append(f"{base} project {f'language:{lang}' if lang else ''}".strip())

        # 3. Запрос по навыкам (фреймворкам)
        for skill in profile.skills[:2]:
            if skill != lang:
                queries.append(f"{skill} starter {f'language:{lang}' if lang else ''}".strip())

        unique_queries = []
        for q in queries:
            if q and q not in unique_queries: unique_queries.append(q)

        return unique_queries[:5]

    def _rank_repositories(self, repositories: list[GitHubRepository], raw_query: str, profile: UserProfile) -> list[GitHubRepository]:
        scored = []
        core_tokens = self._extract_query_tokens(raw_query)
        
        for repo in repositories:
            score = 0.0
            text = f"{repo.name} {repo.description} {' '.join(repo.topics)}".lower()
            
            # Соответствие токенам из запроса
            matches = sum(1 for t in core_tokens if t in text)
            score += matches * 5.0
            
            # Соответствие навыкам
            for skill in profile.skills:
                if skill.lower() in text: score += 3.0
            
            # Популярность (звезды)
            score += min(repo.stars / 100, 10)
            
            scored.append((repo, score))
            
        scored.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in scored]

    def _build_patterns(self, repositories: list[GitHubRepository]) -> list[RepositoryPattern]:
        # Упрощенная логика паттернов для мета-данных
        patterns = []
        for name, rule in self.PATTERN_RULES.items():
            matches = []
            for repo in repositories:
                text = f"{repo.name} {repo.description}".lower()
                if any(r in text for r in rule["required"]):
                    matches.append(repo)
            if matches:
                patterns.append(RepositoryPattern(name=name, score=len(matches)*1.0, repositories=matches))
        return patterns

    def _extract_query_tokens(self, raw_query: str) -> list[str]:
        lowered = raw_query.lower()
        replacements = {
            "телеграм": "telegram", "бот": "bot", "аналитика": "analytics",
            "бэкенд": "backend", "машинное обучение": "ml", "опрос": "survey",
            "рассылка": "mailing", "чат": "chat", "управление": "management",
            "утилита": "tool", "конструктор": "builder", "библиотека": "library"
        }
        for k, v in replacements.items(): lowered = lowered.replace(k, v)
        
        tokens = []
        for t in lowered.replace(",", " ").replace(".", " ").split():
            t = t.strip().strip(":;\"'")
            if len(t) < 2 or t in self.STOP_TERMS: continue
            # Пропускаем кириллицу, если не смогли перевести
            if any("а" <= c <= "я" for c in t): continue
            if t not in tokens: tokens.append(t)
        return tokens

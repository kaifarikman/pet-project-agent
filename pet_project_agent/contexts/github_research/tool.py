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
            "threshold": 4,
        },
        "dashboard": {
            "required": ["dashboard", "analytics", "visualization", "charts", "metrics"],
            "optional": ["insights", "report", "bi", "pandas", "sql"],
            "negative": ["telegram", "discord", "bot", "scanner", "vulnerability"],
            "threshold": 4,
        },
        "tracker": {
            "required": ["tracker", "todo", "task", "habit", "kanban"],
            "optional": ["productivity", "planner", "streak"],
            "negative": ["api", "analytics", "telegram", "discord", "security"],
            "threshold": 4,
        },
        "finance": {
            "required": ["expense", "finance", "budget", "money", "spending"],
            "optional": ["transaction", "wallet", "sql", "analytics"],
            "negative": ["telegram", "discord", "security", "scanner"],
            "threshold": 4,
        },
        "bot": {
            "required": ["bot", "telegram", "discord"],
            "optional": ["chat", "reminder", "assistant", "automation"],
            "negative": ["dashboard", "analytics", "scanner", "vulnerability"],
            "threshold": 4,
        },
        "ml_app": {
            "required": ["machine learning", "predict", "classification", "regression", "inference"],
            "optional": ["ml", "model", "dataset", "training"],
            "negative": ["telegram", "discord", "crud", "kanban"],
            "threshold": 4,
        },
        "security_tool": {
            "required": ["security", "cybersecurity", "scanner", "vulnerability", "log"],
            "optional": ["audit", "threat", "alert", "incident"],
            "negative": ["dashboard", "telegram", "discord", "habit"],
            "threshold": 4,
        },
    }

    LANGUAGE_LABELS = {
        "python": "Python",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "java": "Java",
        "go": "Go",
    }
    DOMAIN_TERMS = {
        "backend": ["backend", "api", "service"],
        "api": ["api", "rest", "crud"],
        "data": ["data", "dataset", "etl"],
        "analytics": ["analytics", "dashboard", "visualization"],
        "automation": ["automation", "workflow", "bot"],
        "bots": ["telegram", "bot", "discord"],
        "ml": ["ml", "predict", "classification"],
        "security": ["security", "scanner", "log"],
    }
    STOP_TERMS = {
        "portfolio",
        "портфолио",
        "week",
        "weeks",
        "month",
        "months",
        "day",
        "days",
        "недел",
        "месяц",
        "день",
        "хочу",
        "найди",
        "реальные",
        "open-source",
        "opensource",
        "примеры",
        "example",
        "examples",
    }
    NOISE_TERMS = {
        "awesome",
        ".github",
        ".config",
        "boilerplate",
        "template",
        "starter",
        "sdk",
        "cheatsheet",
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

    def run(
        self,
        query: str,
        user_profile: UserProfile | None = None,
    ) -> GitHubResearchData:
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
        classified_repositories = self._classify_repositories(ranked_repositories)
        patterns = self._build_patterns(classified_repositories)

        return GitHubResearchData(
            search_queries=search_queries,
            repositories=classified_repositories,
            patterns=patterns,
        )

    def _load_skills_catalog(self) -> list[Skill]:
        if self.skill_catalog_repository is None:
            return []
        return self.skill_catalog_repository.load_skills()

    def _build_profile(self, query: str) -> UserProfile:
        if not self.skills_catalog:
            return UserProfile(raw_text=query)
        return self.profile_service.build_profile(query, self.skills_catalog)

    def _build_search_queries(self, raw_query: str, profile: UserProfile) -> list[str]:
        queries: list[str] = []
        language = self._find_language(profile)
        frameworks = self._find_frameworks(profile)
        data_skills = self._find_data_skills(profile)
        prioritized_domains = self._prioritized_domains(profile, raw_query)

        for framework in frameworks[:2]:
            if framework == "telegram":
                queries.append(self._compose_query("telegram", language, ["bot", "project"]))
                continue
            queries.append(self._compose_query(framework, language, ["api", "project"]))
            queries.append(self._compose_query(framework, language, ["backend", "project"]))

        for data_skill in data_skills[:2]:
            if data_skill == "pandas":
                queries.append(self._compose_query("pandas", language, ["analytics", "project"]))
            elif data_skill == "sql":
                queries.append(self._compose_query("sql", language, ["api", "project"]))
            elif data_skill == "machine_learning":
                queries.append(self._compose_query("ml", language, ["project"]))
            elif data_skill == "scikit_learn":
                queries.append(self._compose_query("scikit-learn", language, ["classification", "project"]))
            elif data_skill == "data_science":
                queries.append(self._compose_query("ml", language, ["classification", "project"]))
            else:
                queries.append(self._compose_query(data_skill, language, ["project"]))

        for domain in prioritized_domains[:2]:
            queries.append(self._compose_query(None, language, self.DOMAIN_TERMS.get(domain, [domain])[:2] + ["project"]))

        core_terms = self._core_terms(profile, raw_query)
        if core_terms:
            queries.append(self._compose_query(None, language, core_terms[:3] + ["project"]))

        unique_queries: list[str] = []
        for item in queries:
            normalized = " ".join(item.split())
            if normalized and normalized not in unique_queries:
                unique_queries.append(normalized)

        return unique_queries[:6] or [self._compose_query(language.lower() if language else "python", None, ["project"])]

    def _rank_repositories(
        self,
        repositories: list[GitHubRepository],
        raw_query: str,
        profile: UserProfile,
    ) -> list[GitHubRepository]:
        scored_repositories = sorted(
            [
                (
                    repository,
                    self._repository_score(repository, raw_query, profile),
                )
                for repository in repositories
            ],
            key=lambda item: item[1],
            reverse=True,
        )
        ranked_repositories: list[GitHubRepository] = []

        for repository, score in scored_repositories:
            if score <= 0:
                continue

            ranked_repositories.append(
                GitHubRepository(
                    name=repository.name,
                    url=repository.url,
                    description=repository.description,
                    language=repository.language,
                    stars=repository.stars,
                    topics=list(repository.topics),
                    repository_types=list(repository.repository_types),
                    relevance_score=score,
                )
            )

        return ranked_repositories

    def _repository_score(
        self,
        repository: GitHubRepository,
        raw_query: str,
        profile: UserProfile,
    ) -> float:
        haystack = " ".join(
            [
                repository.name.lower(),
                (repository.description or "").lower(),
                (repository.language or "").lower(),
                " ".join(topic.lower() for topic in repository.topics),
            ]
        )
        score = 0.0
        core_terms = self._core_terms(profile, raw_query)
        core_matches = sum(1 for term in core_terms if term in haystack)

        if core_terms and core_matches == 0:
            return -100.0

        for skill in profile.skills:
            if skill in haystack:
                score += 3

        for domain in self._prioritized_domains(profile, raw_query):
            for term in self.DOMAIN_TERMS.get(domain, [domain]):
                if term in haystack:
                    score += 2

        score += core_matches * 2.5

        language = self._find_language(profile)
        if language and repository.language and repository.language.lower() == language.lower():
            score += 3

        if repository.description:
            score += 1

        if any(noise_term in repository.name.lower() for noise_term in self.NOISE_TERMS):
            score -= 4

        if repository.name.startswith(".") or "/." in repository.name:
            score -= 6

        score += min(repository.stars, 1000) / 500
        return score

    def _classify_repositories(
        self,
        repositories: list[GitHubRepository],
    ) -> list[GitHubRepository]:
        classified_repositories: list[GitHubRepository] = []

        for repository in repositories:
            haystack = self._repository_text(repository)
            repository_types: list[tuple[str, float]] = []

            for pattern_name, rule in self.PATTERN_RULES.items():
                score = self._pattern_repository_score(haystack, rule)
                if score >= rule["threshold"]:
                    repository_types.append((pattern_name, score))

            repository_types.sort(key=lambda item: item[1], reverse=True)
            classified_repositories.append(
                GitHubRepository(
                    name=repository.name,
                    url=repository.url,
                    description=repository.description,
                    language=repository.language,
                    stars=repository.stars,
                    topics=list(repository.topics),
                    repository_types=[item[0] for item in repository_types],
                    relevance_score=repository.relevance_score,
                )
            )

        return classified_repositories

    def _build_patterns(
        self,
        repositories: list[GitHubRepository],
    ) -> list[RepositoryPattern]:
        patterns: list[RepositoryPattern] = []

        for pattern_name, rule in self.PATTERN_RULES.items():
            pattern_repositories: list[tuple[GitHubRepository, float]] = []

            for repository in repositories:
                if pattern_name not in repository.repository_types:
                    continue

                score = self._pattern_repository_score(
                    self._repository_text(repository),
                    rule,
                )
                pattern_repositories.append((repository, score))

            if not pattern_repositories:
                continue

            ordered_repositories = [
                repository
                for repository, _ in sorted(
                    pattern_repositories,
                    key=lambda item: (item[1], item[0].stars),
                    reverse=True,
                )
            ]

            patterns.append(
                RepositoryPattern(
                    name=pattern_name,
                    score=sum(score for _, score in pattern_repositories),
                    repositories=ordered_repositories,
                )
            )

        return sorted(patterns, key=lambda pattern: pattern.score, reverse=True)

    def _find_language(self, profile: UserProfile) -> str | None:
        for skill in profile.skills:
            if skill in self.LANGUAGE_LABELS:
                return self.LANGUAGE_LABELS[skill]
        return None

    @staticmethod
    def _find_frameworks(profile: UserProfile) -> list[str]:
        known_frameworks = {
            "fastapi": "fastapi",
            "django": "django",
            "flask": "flask",
            "telegram_bot": "telegram",
        }
        return [known_frameworks[skill] for skill in profile.skills if skill in known_frameworks]

    @staticmethod
    def _find_data_skills(profile: UserProfile) -> list[str]:
        data_skills = {"pandas", "numpy", "sql", "machine_learning", "scikit_learn", "data_science"}
        return [skill for skill in profile.skills if skill in data_skills]

    def _compose_query(
        self,
        primary: str | None,
        language: str | None,
        terms: list[str],
    ) -> str:
        query_parts: list[str] = []

        if primary:
            query_parts.append(primary)

        for term in terms:
            if term not in query_parts:
                query_parts.append(term)

        if "project" not in query_parts:
            query_parts.append("project")

        if language:
            query_parts.append(f"language:{language}")

        final_parts: list[str] = []
        for item in query_parts:
            if item not in final_parts:
                final_parts.append(item)

        if language:
            core_parts = [item for item in final_parts if not item.startswith("language:")]
            return " ".join(core_parts[:4] + [f"language:{language}"])

        return " ".join(final_parts[:4])

    def _prioritized_domains(self, profile: UserProfile, raw_query: str) -> list[str]:
        domain_scores: dict[str, float] = {}
        skills_by_name = {skill.name: skill for skill in self.skills_catalog}

        for skill_name in profile.skills:
            skill = skills_by_name.get(skill_name)
            if skill is None:
                continue

            weight = 0.5 if skill.category == "language" else 2.0
            for domain in skill.domains:
                domain_scores[domain] = domain_scores.get(domain, 0.0) + weight

        token_to_domain = {
            "api": "api",
            "rest": "api",
            "backend": "backend",
            "analytics": "analytics",
            "dashboard": "analytics",
            "data": "data",
            "dataset": "data",
            "bot": "bots",
            "telegram": "bots",
            "discord": "bots",
            "ml": "ml",
            "predict": "ml",
            "classification": "ml",
            "security": "security",
        }

        for token in self._extract_query_tokens(raw_query):
            domain = token_to_domain.get(token)
            if domain:
                domain_scores[domain] = domain_scores.get(domain, 0.0) + 2.5

        ranked_domains = sorted(domain_scores, key=lambda item: domain_scores[item], reverse=True)
        return ranked_domains[:3]

    def _core_terms(self, profile: UserProfile, raw_query: str) -> list[str]:
        terms: list[str] = []

        skill_term_map = {
            "fastapi": ["fastapi", "api"],
            "django": ["django", "api"],
            "flask": ["flask", "api"],
            "pandas": ["pandas", "analytics", "data"],
            "sql": ["sql", "database", "api"],
            "telegram_bot": ["telegram", "bot"],
            "machine_learning": ["ml", "machine-learning", "predict"],
            "scikit_learn": ["scikit-learn", "classification", "predict"],
            "data_science": ["data", "analytics", "predict"],
            "cybersecurity": ["security", "scanner", "log"],
        }

        for skill in profile.skills:
            for term in skill_term_map.get(skill, [skill]):
                if term not in terms and term not in self.STOP_TERMS:
                    terms.append(term)

        for token in self._extract_query_tokens(raw_query):
            if token not in terms:
                terms.append(token)

        return terms[:8]

    @staticmethod
    def _repository_text(repository: GitHubRepository) -> str:
        return " ".join(
            [
                repository.name.lower(),
                (repository.description or "").lower(),
                (repository.language or "").lower(),
                " ".join(topic.lower() for topic in repository.topics),
            ]
        )

    @staticmethod
    def _pattern_repository_score(haystack: str, rule: dict[str, object]) -> float:
        required_hits = [keyword for keyword in rule["required"] if keyword in haystack]
        optional_hits = [keyword for keyword in rule["optional"] if keyword in haystack]
        negative_hits = [keyword for keyword in rule["negative"] if keyword in haystack]

        if not required_hits:
            return 0.0

        score = len(required_hits) * 3.0
        score += len(optional_hits) * 1.5
        score -= len(negative_hits) * 2.5
        return score

    def _extract_query_tokens(self, raw_query: str) -> list[str]:
        lowered = raw_query.lower()
        replacements = {
            "телеграм": "telegram",
            "бот": "bot",
            "аналитика": "analytics",
            "аналитик": "analytics",
            "бэкенд": "backend",
            "машинное обучение": "ml",
            "кибербезопасность": "security",
            "дата саенс": "data science",
            "дата сайнс": "data science",
            "предсказать": "predict",
            "предсказание": "predict",
            "датасет": "dataset",
            "данные": "data",
        }

        for source, target in replacements.items():
            lowered = lowered.replace(source, target)

        tokens = []
        for token in lowered.replace(",", " ").replace(".", " ").split():
            cleaned = token.strip().strip(":").strip(";").strip('"').strip("'")
            if not cleaned or len(cleaned) < 2:
                continue
            if cleaned in self.STOP_TERMS:
                continue
            if any("а" <= char <= "я" or char == "ё" for char in cleaned):
                continue
            if cleaned not in tokens:
                tokens.append(cleaned)

        return tokens

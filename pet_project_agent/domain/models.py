from dataclasses import dataclass, field


@dataclass
class ToolCall:
    tool_name: str
    query: str


@dataclass
class ToolPlan:
    needs_clarification: bool
    clarification_question: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    reason: str = ""


@dataclass
class UserProfile:
    raw_text: str
    skills: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    goal: str | None = None
    duration: str | None = None
    level: str | None = None


@dataclass
class Skill:
    name: str
    aliases: list[str]
    category: str
    domains: list[str]


@dataclass
class GitHubRepository:
    name: str
    url: str
    description: str | None
    language: str | None
    stars: int
    topics: list[str] = field(default_factory=list)
    repository_types: list[str] = field(default_factory=list)
    relevance_score: float = 0.0


@dataclass
class RepositoryPattern:
    name: str
    score: float
    repositories: list[GitHubRepository] = field(default_factory=list)


@dataclass
class GitHubResearchData:
    search_queries: list[str] = field(default_factory=list)
    repositories: list[GitHubRepository] = field(default_factory=list)
    patterns: list[RepositoryPattern] = field(default_factory=list)


@dataclass
class HackerNewsItem:
    title: str
    url: str | None
    points: int
    author: str
    created_at: str


@dataclass
class ResearchResult:
    tool_calls: list[ToolCall] = field(default_factory=list)
    user_profile: UserProfile | None = None
    github_queries: list[str] = field(default_factory=list)
    github_repositories: list[GitHubRepository] = field(default_factory=list)
    github_patterns: list[RepositoryPattern] = field(default_factory=list)
    hackernews_items: list[HackerNewsItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ProjectIdea:
    title: str
    description: str
    stack: list[str]
    mvp_features: list[str]
    why_it_fits: str
    references: list[str] = field(default_factory=list)

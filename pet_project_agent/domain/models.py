from dataclasses import dataclass, field


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


@dataclass
class ProjectIdea:
    title: str
    description: str
    stack: list[str]
    mvp_features: list[str]
    why_it_fits: str
    references: list[GitHubRepository] = field(default_factory=list)
from typing import Protocol

from pet_project_agent.domain.models import (
    GitHubRepository,
    HackerNewsItem,
    ToolPlan,
    UserProfile,
)


class LLMClientPort(Protocol):
    def generate(self, prompt: str, json_mode: bool = False) -> str:
        ...


class ProfileToolPort(Protocol):
    def run(self, query: str) -> UserProfile:
        ...


class GitHubSearchToolPort(Protocol):
    def run(self, query: str) -> list[GitHubRepository]:
        ...


class HackerNewsSearchToolPort(Protocol):
    def run(self, query: str) -> list[HackerNewsItem]:
        ...


class ToolRouterPort(Protocol):
    def build_plan(self, user_query: str) -> ToolPlan:
        ...

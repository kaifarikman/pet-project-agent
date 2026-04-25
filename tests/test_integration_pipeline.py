from pet_project_agent.application.agent_orchestrator import AgentOrchestrator
from pet_project_agent.application.response_renderer import ResponseRenderer
from pet_project_agent.application.tool_executor import ToolExecutor
from pet_project_agent.application.tool_router import ToolRouter
from pet_project_agent.contexts.ideation.service import IdeationService
from pet_project_agent.domain.models import (
    GitHubResearchData,
    GitHubRepository,
    RepositoryPattern,
    UserProfile,
)


class OfflineLLM:
    def generate(self, prompt: str, json_mode: bool = False) -> str:
        return '{"ideas": [{"title": "Test Project", "description": "Test Desc", "stack": ["python"], "mvp_features": ["f1"], "why_it_fits": "fits", "references": []}]}'


class FakeProfileTool:
    name = "profile_tool"

    def run(self, query: str) -> UserProfile:
        return UserProfile(
            raw_text=query,
            skills=["python"],
            domains=["automation", "backend"],
        )


class FakeGitHubTool:
    name = "github_search_tool"

    def run(self, query: str, user_profile: UserProfile | None = None) -> GitHubResearchData:
        repository = GitHubRepository(
            name="example/agent-cli",
            url="https://github.com/example/agent-cli",
            description="CLI agent with tools",
            language="Python",
            stars=42,
            repository_types=["api_service"],
            relevance_score=8.0,
        )
        return GitHubResearchData(
            search_queries=["python agent project"],
            repositories=[repository],
            patterns=[
                RepositoryPattern(
                    name="api_service",
                    score=8.0,
                    repositories=[repository],
                )
            ],
        )


class FakeHNTool:
    name = "hackernews_search_tool"

    def run(self, query: str) -> list:
        return []


def test_full_pipeline_renders_project_response_with_mock_llm() -> None:
    llm = OfflineLLM()
    router = ToolRouter(llm, routing_mode="rules_only")
    executor = ToolExecutor(
        tools={
            "profile_tool": FakeProfileTool(),
            "github_search_tool": FakeGitHubTool(),
            "hackernews_search_tool": FakeHNTool(),
        }
    )
    orchestrator = AgentOrchestrator(
        tool_router=router,
        tool_executor=executor,
        ideation_service=IdeationService(llm_client=llm),
        response_renderer=ResponseRenderer(),
    )

    response = orchestrator.run(
        "хочу написать пет-проект с агентной системой на python и найти реальные open-source примеры"
    )

    assert "Топ-3 pet-проекта" in response
    assert "Test Project" in response
    assert "Что агент понял о пользователе" not in response


def test_full_pipeline_can_render_debug_details() -> None:
    llm = OfflineLLM()
    router = ToolRouter(llm, routing_mode="rules_only")
    executor = ToolExecutor(
        tools={
            "profile_tool": FakeProfileTool(),
            "github_search_tool": FakeGitHubTool(),
            "hackernews_search_tool": FakeHNTool(),
        }
    )
    orchestrator = AgentOrchestrator(
        tool_router=router,
        tool_executor=executor,
        ideation_service=IdeationService(llm_client=llm),
        response_renderer=ResponseRenderer(),
    )

    response = orchestrator.run(
        "хочу написать пет-проект с агентной системой на python и найти реальные open-source примеры",
        include_debug=True,
    )

    assert "Какие инструменты и источники использованы" in response
    assert "profile_tool" in response
    assert "github_search_tool" in response

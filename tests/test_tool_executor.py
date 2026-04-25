from pet_project_agent.application.tool_executor import ToolExecutor
from pet_project_agent.domain.models import GitHubRepository, RepositoryPattern


def test_merge_patterns_preserves_repositories_from_multiple_payloads() -> None:
    first_repository = GitHubRepository(
        name="repo-one",
        url="https://example.com/repo-one",
        description="first",
        language="Python",
        stars=10,
        relevance_score=5.0,
    )
    second_repository = GitHubRepository(
        name="repo-two",
        url="https://example.com/repo-two",
        description="second",
        language="Python",
        stars=20,
        relevance_score=6.0,
    )

    merged = ToolExecutor._merge_patterns(
        [
            RepositoryPattern(
                name="api_service",
                score=3.0,
                repositories=[first_repository],
            )
        ],
        [
            RepositoryPattern(
                name="api_service",
                score=4.0,
                repositories=[second_repository],
            )
        ],
    )

    assert len(merged) == 1
    assert merged[0].name == "api_service"
    assert merged[0].score == 7.0
    assert [repository.url for repository in merged[0].repositories] == [
        "https://example.com/repo-two",
        "https://example.com/repo-one",
    ]

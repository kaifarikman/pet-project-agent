from pet_project_agent.contexts.profile.service import ProfileService
from pet_project_agent.infrastructure.data.skill_catalog_repository import (
    SkillCatalogRepository,
)


def test_profile_service_avoids_py_false_positive() -> None:
    skills = SkillCatalogRepository("data/skills_catalog.csv").load_skills()
    profile = ProfileService().build_profile(
        "I am happy with FastAPI and APIs in general.",
        skills,
    )

    assert "python" not in profile.skills
    assert "fastapi" in profile.skills


def test_profile_service_detects_python_from_pitone() -> None:
    skills = SkillCatalogRepository("data/skills_catalog.csv").load_skills()
    profile = ProfileService().build_profile(
        "пишу в основном на питоне и хочу сделать агентный проект",
        skills,
    )

    assert "python" in profile.skills

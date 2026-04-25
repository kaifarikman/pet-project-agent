from pet_project_agent.contexts.profile.service import ProfileService
from pet_project_agent.domain.models import UserProfile
from pet_project_agent.infrastructure.data.skill_catalog_repository import SkillCatalogRepository


class ProfileTool:
    name = "profile_tool"

    def __init__(
        self,
        skill_catalog_repository: SkillCatalogRepository,
        service: ProfileService | None = None,
    ) -> None:
        self.skill_catalog_repository = skill_catalog_repository
        self.service = service or ProfileService()
        self.skills_catalog = self.skill_catalog_repository.load_skills()

    def run(self, query: str) -> UserProfile:
        return self.service.build_profile(query, self.skills_catalog)

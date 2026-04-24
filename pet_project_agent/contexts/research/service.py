from pet_project_agent.domain.models import UserProfile


class ResearchService:
    def build_github_queries(self, profile: UserProfile) -> list[str]:
        queries: list[str] = []

        skills = profile.skills
        domains = profile.domains

        if skills:
            queries.append(" ".join(skills) + " project")

        if skills and profile.goal:
            queries.append(" ".join(skills) + f" {profile.goal} project")

        if domains:
            main_domains = domains[:2]
            queries.append(" ".join(main_domains) + " project")

        if skills and domains:
            main_skills = skills[:3]
            main_domains = domains[:2]
            queries.append(" ".join(main_skills + main_domains) + " github")

        unique_queries = []
        for query in queries:
            if query not in unique_queries:
                unique_queries.append(query)

        return unique_queries[:5]

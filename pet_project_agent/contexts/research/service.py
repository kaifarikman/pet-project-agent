from pet_project_agent.domain.models import UserProfile


class ResearchService:
    def build_github_queries(self, profile: UserProfile) -> list[str]:
        queries: list[str] = []

        skills = profile.skills
        domains = profile.domains

        main_language = self._find_main_language(skills)
        frameworks = self._find_frameworks(skills)
        data_tools = self._find_data_tools(skills)

        if main_language and frameworks:
            for framework in frameworks:
                queries.append(f"{framework} {main_language} project")
                queries.append(f"{framework} {main_language} api")

        if main_language and "backend" in domains:
            queries.append(f"{main_language} backend api")
            queries.append(f"{main_language} rest api")

        if main_language and data_tools:
            for tool in data_tools:
                queries.append(f"{main_language} {tool} project")
                queries.append(f"{tool} analytics project")

        if main_language and profile.goal == "portfolio":
            queries.append(f"{main_language} portfolio project")

        for domain in domains[:3]:
            if main_language:
                queries.append(f"{main_language} {domain} project")
            else:
                queries.append(f"{domain} project")

        return self._unique(queries)[:8]

    @staticmethod
    def _find_main_language(skills: list[str]) -> str | None:
        languages = {"python", "javascript", "typescript", "java", "go", "c++", "c#"}
        for skill in skills:
            if skill in languages:
                return skill
        return None

    @staticmethod
    def _find_frameworks(skills: list[str]) -> list[str]:
        frameworks = {"fastapi", "django", "flask", "react", "vue", "spring"}
        return [skill for skill in skills if skill in frameworks]

    @staticmethod
    def _find_data_tools(skills: list[str]) -> list[str]:
        data_tools = {"pandas", "numpy", "scikit-learn", "sklearn"}
        return [skill for skill in skills if skill in data_tools]

    @staticmethod
    def _unique(items: list[str]) -> list[str]:
        result: list[str] = []

        for item in items:
            if item not in result:
                result.append(item)

        return result
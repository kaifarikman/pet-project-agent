from pet_project_agent.domain.models import Skill, UserProfile


class ProfileService:
    def build_profile(self, user_text: str, skills_catalog: list[Skill]) -> UserProfile:
        text = user_text.lower()

        found_skills: list[str] = []
        found_domains: set[str] = set()

        for skill in skills_catalog:
            aliases = [skill.name, *skill.aliases]

            if any(alias.lower() in text for alias in aliases):
                found_skills.append(skill.name)
                found_domains.update(skill.domains)

        return UserProfile(
            raw_text=user_text,
            skills=found_skills,
            domains=sorted(found_domains),
            goal=self._extract_goal(text),
            duration=self._extract_duration(text),
            level=self._extract_level(text),
        )

    @staticmethod
    def _extract_goal(text: str) -> str | None:
        if "портфолио" in text or "portfolio" in text:
            return "portfolio"
        if "стаж" in text or "работ" in text or "job" in text:
            return "job"
        if "учеб" in text or "learn" in text:
            return "learning"
        return None

    @staticmethod
    def _extract_duration(text: str) -> str | None:
        if "недел" in text or "week" in text:
            return "weeks"
        if "месяц" in text or "month" in text:
            return "months"
        if "день" in text or "day" in text:
            return "days"
        return None

    @staticmethod
    def _extract_level(text: str) -> str | None:
        if "начина" in text or "junior" in text or "easy" in text:
            return "junior"
        if "средн" in text or "middle" in text or "medium" in text:
            return "middle"
        if "сложн" in text or "senior" in text or "hard" in text:
            return "advanced"
        return None

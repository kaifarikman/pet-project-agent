import re

from pet_project_agent.domain.models import Skill, UserProfile
from pet_project_agent.knowledge.base import KnowledgeBase


class ProfileService:
    def __init__(self, knowledge_base: KnowledgeBase | None = None) -> None:
        self.knowledge_base = knowledge_base or KnowledgeBase.default()

    def build_profile(self, user_text: str, skills_catalog: list[Skill]) -> UserProfile:
        text = user_text.lower()
        normalized_text = self._normalize_text(user_text)

        found_skills: list[str] = []
        found_domains: set[str] = set()

        for skill in skills_catalog:
            aliases = [skill.name, *skill.aliases]

            if any(self._contains_alias(normalized_text, alias) for alias in aliases):
                found_skills.append(skill.name)
                found_domains.update(skill.domains)

        found_domains.update(self._infer_domains_from_text(normalized_text, self.knowledge_base))

        return UserProfile(
            raw_text=user_text,
            skills=found_skills,
            domains=sorted(found_domains),
            goal=self._extract_goal(text),
            duration=self._extract_duration(text),
            level=self._extract_level(text),
        )

    def _extract_goal(self, text: str) -> str | None:
        markers = self.knowledge_base.routing.goal_markers
        if any(marker in text for marker in markers[:2]):
            return "portfolio"
        if any(marker in text for marker in markers[2:5]):
            return "job"
        if any(marker in text for marker in markers[5:]):
            return "learning"
        return None

    def _extract_duration(self, text: str) -> str | None:
        markers = self.knowledge_base.routing.duration_markers
        if any(marker in text for marker in markers[:2]):
            return "weeks"
        if any(marker in text for marker in markers[2:4]):
            return "months"
        if any(marker in text for marker in markers[4:]):
            return "days"
        return None

    def _extract_level(self, text: str) -> str | None:
        markers = self.knowledge_base.routing.level_markers
        if any(marker in text for marker in markers[:3]):
            return "junior"
        if any(marker in text for marker in markers[3:6]):
            return "middle"
        if any(marker in text for marker in markers[6:]):
            return "advanced"
        return None

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = text.lower().replace("_", " ").replace("-", " ")
        return re.sub(r"\s+", " ", normalized).strip()

    @classmethod
    def _contains_alias(cls, normalized_text: str, alias: str) -> bool:
        normalized_alias = cls._normalize_text(alias)
        if not normalized_alias:
            return False

        pattern = rf"(?<![0-9A-Za-zА-Яа-яЁё_]){re.escape(normalized_alias)}(?![0-9A-Za-zА-Яа-яЁё_])"
        return re.search(pattern, normalized_text) is not None

    @classmethod
    def _infer_domains_from_text(cls, normalized_text: str, knowledge_base: KnowledgeBase | None = None) -> set[str]:
        knowledge = knowledge_base or KnowledgeBase.default()
        inferred_domains: set[str] = set()

        for domain, hints in knowledge.profile_domain_hints.items():
            if any(cls._contains_alias(normalized_text, hint) for hint in hints):
                inferred_domains.add(domain)

        return inferred_domains

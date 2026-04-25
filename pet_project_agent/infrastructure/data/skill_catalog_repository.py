import csv
from pathlib import Path

from pet_project_agent.domain.models import Skill


class SkillCatalogRepository:
    def __init__(self, catalog_path: str | Path) -> None:
        self.catalog_path = Path(catalog_path)

    def load_skills(self) -> list[Skill]:
        with self.catalog_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            skills: list[Skill] = []

            for row in reader:
                skills.append(
                    Skill(
                        name=(row.get("skill") or "").strip(),
                        aliases=self._split_field(row.get("aliases")),
                        category=(row.get("category") or "").strip(),
                        domains=self._split_field(row.get("domains")),
                    )
                )

        return [skill for skill in skills if skill.name]

    @staticmethod
    def _split_field(value: str | None) -> list[str]:
        return [item.strip() for item in (value or "").split(";") if item.strip()]

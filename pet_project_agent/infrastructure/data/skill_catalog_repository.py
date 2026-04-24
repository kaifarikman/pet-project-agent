import pandas as pd
from pathlib import Path
from pet_project_agent.domain.models import Skill

class SkillCatalogRepository:
    def __init__(self, catalog_path: str | Path) -> None:
        self.catalog_path = Path(catalog_path)

    def load_skills(self) -> list[Skill]:
        df = pd.read_csv(self.catalog_path, sep=',', encoding='utf-8')
        df = df.fillna("")

        return [
            Skill(
                name=row["skill"],
                aliases=[i.strip() for i in row["aliases"].split(";") if i.strip()],
                category=row["category"],
                domains=[i.strip() for i in row["domains"].split(";") if i.strip()],
            )
            for row in df.to_dict("records")
        ]

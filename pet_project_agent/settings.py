import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    skill_catalog_path: str = "data/skills_catalog.csv"
    routing_mode: str = "rules_first"
    github_search_limit: int = 5
    github_min_stars: int = 0
    hackernews_search_limit: int = 5

    @classmethod
    def from_env(cls) -> "AppSettings":
        from dotenv import load_dotenv
        load_dotenv()
        return cls(
            skill_catalog_path=os.getenv("SKILL_CATALOG_PATH", "data/skills_catalog.csv"),
            routing_mode=os.getenv("ROUTING_MODE", "rules_first").strip().lower() or "rules_first",
            github_search_limit=cls._parse_int("GITHUB_SEARCH_LIMIT", 5),
            github_min_stars=cls._parse_int("GITHUB_MIN_STARS", 0),
            hackernews_search_limit=cls._parse_int("HACKERNEWS_SEARCH_LIMIT", 5),
        )

    @staticmethod
    def _parse_int(env_name: str, default: int) -> int:
        raw_value = os.getenv(env_name)
        if raw_value is None:
            return default

        try:
            return int(raw_value)
        except ValueError:
            return default

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class RoutingKnowledge:
    goal_markers: tuple[str, ...]
    duration_markers: tuple[str, ...]
    level_markers: tuple[str, ...]
    profile_phrase_markers: tuple[str, ...]
    explicit_research_markers: tuple[str, ...]
    hackernews_markers: tuple[str, ...]
    project_markers: tuple[str, ...]
    technical_markers: tuple[str, ...]
    github_technical_markers: tuple[str, ...]
    subject_markers: tuple[str, ...]
    vague_markers: tuple[str, ...]


@dataclass(frozen=True)
class KnowledgeBase:
    profile_domain_hints: dict[str, tuple[str, ...]]
    routing: RoutingKnowledge

    @classmethod
    def from_file(cls, path: str | Path) -> "KnowledgeBase":
        registry_path = Path(path)
        with registry_path.open("rb") as registry_file:
            raw_registry = tomllib.load(registry_file)

        profile_domain_hints = {
            domain: tuple(hints)
            for domain, hints in raw_registry.get("profile", {}).get("domain_hints", {}).items()
        }
        routing_section = raw_registry.get("routing", {})

        return cls(
            profile_domain_hints=profile_domain_hints,
            routing=RoutingKnowledge(
                goal_markers=tuple(routing_section.get("goal_markers", [])),
                duration_markers=tuple(routing_section.get("duration_markers", [])),
                level_markers=tuple(routing_section.get("level_markers", [])),
                profile_phrase_markers=tuple(routing_section.get("profile_phrase_markers", [])),
                explicit_research_markers=tuple(routing_section.get("explicit_research_markers", [])),
                hackernews_markers=tuple(routing_section.get("hackernews_markers", [])),
                project_markers=tuple(routing_section.get("project_markers", [])),
                technical_markers=tuple(routing_section.get("technical_markers", [])),
                github_technical_markers=tuple(routing_section.get("github_technical_markers", [])),
                subject_markers=tuple(routing_section.get("subject_markers", [])),
                vague_markers=tuple(routing_section.get("vague_markers", [])),
            ),
        )

    @classmethod
    def default(cls) -> "KnowledgeBase":
        return cls.from_file(Path(__file__).with_name("registry.toml"))

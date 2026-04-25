from pet_project_agent.domain.models import ProjectIdea, ResearchResult


class ResponseRenderer:
    def render(
        self,
        research_result: ResearchResult,
        ideas: list[ProjectIdea],
        include_debug: bool = False,
    ) -> str:
        executed_tools = {tool_call.tool_name for tool_call in research_result.tool_calls}

        lines: list[str] = []
        lines.append("# Топ-3 pet-проекта")
        lines.append("")

        for index, idea in enumerate(ideas[:3], start=1):
            lines.append(f"## {index}. {idea.title}")
            lines.append(f"{idea.description}")
            lines.append("")
            lines.append(f"**Почему подходит:** {idea.why_it_fits}")
            lines.append("")
            lines.append(f"**Стек:** {', '.join(idea.stack)}")
            lines.append("")
            lines.append("### MVP возможности")
            for feature in idea.mvp_features:
                lines.append(f"- {feature}")
            
            lines.append("")
            lines.append("### GitHub референсы")
            if idea.references:
                for reference in idea.references:
                    lines.append(f"- [{reference}]({reference})")
            else:
                lines.append("*Конкретных примеров не найдено, идея предложена на основе общих практик.*")
            lines.append("")
            lines.append("---")
            lines.append("")

        if include_debug:
            lines.append("# Отладочная информация")
            lines.append("")
            lines.append("### Использованные инструменты")
            if not research_result.tool_calls:
                lines.append("- Инструменты не вызывались.")
            else:
                for tool_call in research_result.tool_calls:
                    lines.append(f"- **{tool_call.tool_name}**: `{tool_call.query}`")

            lines.append("")
            lines.append("### Результаты поиска")
            if "github_search_tool" in executed_tools:
                lines.append(f"- **GitHub**: найдено {len(research_result.github_repositories)} репозиториев.")
                if research_result.github_queries:
                    lines.append("  - **Расширенные запросы:**")
                    for q in research_result.github_queries:
                        lines.append(f"    - `{q}`")
            if "hackernews_search_tool" in executed_tools:
                lines.append(f"- **Hacker News**: найдено {len(research_result.hackernews_items)} обсуждений.")

            if research_result.warnings:
                lines.append("")
                lines.append("### Предупреждения")
                for warning in research_result.warnings:
                    lines.append(f"- {warning}")

        return "\n".join(lines)

from pet_project_agent.domain.models import ProjectIdea, ResearchResult


class ResponseRenderer:
    SKILL_LABELS = {
        "data_science": "data science",
        "machine_learning": "machine learning",
        "scikit_learn": "scikit-learn",
        "telegram_bot": "telegram bot",
    }

    def render(
        self,
        research_result: ResearchResult,
        ideas: list[ProjectIdea],
        include_debug: bool = False,
    ) -> str:
        profile = research_result.user_profile
        executed_tools = {tool_call.tool_name for tool_call in research_result.tool_calls}

        lines: list[str] = []
        lines.append("Топ-3 pet-проекта")
        for index, idea in enumerate(ideas[:3], start=1):
            lines.append(f"{index}. {idea.title}")
            lines.append(idea.description)
            lines.append(f"Почему подходит: {idea.why_it_fits}")
            lines.append(f"Стек: {', '.join(idea.stack)}")
            lines.append("MVP features:")
            for feature in idea.mvp_features:
                lines.append(f"- {feature}")
            if idea.references:
                lines.append("GitHub references:")
                for reference in idea.references:
                    lines.append(f"- {reference}")
            else:
                lines.append("GitHub references: конкретных references для этой идеи не найдено.")
            lines.append("")

        limitations: list[str] = []
        if research_result.warnings:
            limitations.extend(research_result.warnings)
        if "github_search_tool" in executed_tools and not research_result.github_repositories:
            limitations.append("Внешняя GitHub-выдача ограничена или пустая, поэтому часть идей построена по профилю пользователя.")
        if not limitations and include_debug:
            limitations.append("Выдача собрана из доступных tool results; итоговые идеи всё ещё стоит сузить под конкретный домен.")

        if include_debug:
            lines.append("")
            lines.append("Какие инструменты и источники использованы")
            if not research_result.tool_calls:
                lines.append("- Инструменты не были вызваны.")
            else:
                for tool_call in research_result.tool_calls:
                    lines.append(f"- {tool_call.tool_name}: {tool_call.query}")

            if "github_search_tool" in executed_tools:
                if research_result.github_repositories:
                    lines.append(
                        f"- GitHub: найдено {len(research_result.github_repositories)} репозиториев."
                    )
                    if research_result.github_queries:
                        lines.append("- GitHub queries:")
                        for query in research_result.github_queries:
                            lines.append(f"  {query}")
                    if research_result.github_patterns:
                        lines.append("- GitHub patterns:")
                        for pattern in research_result.github_patterns:
                            lines.append(f"  {pattern.name} (score={pattern.score})")
                else:
                    lines.append("- GitHub: релевантные репозитории не найдены.")

            if "hackernews_search_tool" in executed_tools:
                if research_result.hackernews_items:
                    lines.append(
                        f"- Hacker News: найдено {len(research_result.hackernews_items)} обсуждений."
                    )
                else:
                    lines.append("- Hacker News: релевантные обсуждения не найдены.")

            if limitations:
                lines.append("")
                lines.append("Ограничения")
                for limitation in limitations:
                    lines.append(f"- {limitation}")

        return "\n".join(lines)

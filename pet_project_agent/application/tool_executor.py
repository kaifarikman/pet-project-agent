from pet_project_agent.domain.models import GitHubRepository, RepositoryPattern, ResearchResult, ToolCall, ToolPlan


class ToolExecutor:
    def __init__(self, tools: dict[str, object]) -> None:
        self.tools = tools

    def execute(self, plan: ToolPlan) -> ResearchResult:
        result = ResearchResult()

        for tool_call in self._ordered_tool_calls(plan.tool_calls):
            tool = self.tools.get(tool_call.tool_name)

            if tool is None:
                result.warnings.append(f"Tool `{tool_call.tool_name}` is not configured.")
                continue

            try:
                payload = self._run_tool(tool, tool_call, result)
            except Exception as error:
                result.warnings.append(f"{tool_call.tool_name} failed: {error}")
                continue

            result.tool_calls.append(tool_call)
            self._store_payload(result, tool_call, payload)

        return result

    @staticmethod
    def _ordered_tool_calls(tool_calls: list[ToolCall]) -> list[ToolCall]:
        profile_calls = [tool_call for tool_call in tool_calls if tool_call.tool_name == "profile_tool"]
        other_calls = [tool_call for tool_call in tool_calls if tool_call.tool_name != "profile_tool"]
        return profile_calls + other_calls

    @staticmethod
    def _run_tool(tool: object, tool_call: ToolCall, result: ResearchResult) -> object:
        if tool_call.tool_name == "github_search_tool":
            return tool.run(tool_call.query, user_profile=result.user_profile)

        return tool.run(tool_call.query)

    def _store_payload(self, result: ResearchResult, tool_call: ToolCall, payload: object) -> None:
        if tool_call.tool_name == "profile_tool":
            result.user_profile = payload
            return

        if tool_call.tool_name == "github_search_tool":
            result.github_queries = self._merge_strings(
                result.github_queries,
                getattr(payload, "search_queries", []),
            )
            result.github_repositories = self._merge_repositories(
                result.github_repositories,
                getattr(payload, "repositories", []),
            )
            result.github_patterns = self._merge_patterns(
                result.github_patterns,
                getattr(payload, "patterns", []),
            )
            return

        if tool_call.tool_name == "hackernews_search_tool":
            result.hackernews_items = self._merge_hn_items(
                result.hackernews_items,
                payload,
            )

    @staticmethod
    def _merge_repositories(existing: list, incoming: object) -> list:
        repositories = list(existing)
        seen_urls = {repository.url for repository in repositories}

        for repository in incoming or []:
            if repository.url in seen_urls:
                continue
            repositories.append(repository)
            seen_urls.add(repository.url)

        return repositories

    @staticmethod
    def _merge_hn_items(existing: list, incoming: object) -> list:
        items = list(existing)
        seen_keys = {(item.title, item.url) for item in items}

        for item in incoming or []:
            key = (item.title, item.url)
            if key in seen_keys:
                continue
            items.append(item)
            seen_keys.add(key)

        return items

    @staticmethod
    def _merge_patterns(existing: list, incoming: object) -> list:
        patterns_by_name = {
            pattern.name: RepositoryPattern(
                name=pattern.name,
                score=pattern.score,
                repositories=list(pattern.repositories),
            )
            for pattern in existing
        }

        for pattern in incoming or []:
            current = patterns_by_name.get(pattern.name)
            if current is None:
                patterns_by_name[pattern.name] = RepositoryPattern(
                    name=pattern.name,
                    score=pattern.score,
                    repositories=list(pattern.repositories),
                )
                continue

            current.score += pattern.score
            current.repositories = ToolExecutor._merge_pattern_repositories(
                current.repositories,
                pattern.repositories,
            )

        return sorted(
            patterns_by_name.values(),
            key=lambda pattern: pattern.score,
            reverse=True,
        )

    @staticmethod
    def _merge_strings(existing: list[str], incoming: object) -> list[str]:
        items = list(existing)

        for value in incoming or []:
            if value not in items:
                items.append(value)

        return items

    @staticmethod
    def _merge_pattern_repositories(
        existing: list[GitHubRepository],
        incoming: list[GitHubRepository],
    ) -> list[GitHubRepository]:
        repositories_by_url: dict[str, GitHubRepository] = {
            repository.url: repository for repository in existing
        }

        for repository in incoming:
            current = repositories_by_url.get(repository.url)
            if current is None:
                repositories_by_url[repository.url] = repository
                continue

            if (repository.relevance_score, repository.stars) > (
                current.relevance_score,
                current.stars,
            ):
                repositories_by_url[repository.url] = repository

        return sorted(
            repositories_by_url.values(),
            key=lambda repository: (repository.relevance_score, repository.stars),
            reverse=True,
        )

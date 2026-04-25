from dataclasses import dataclass

from pet_project_agent.domain.models import ToolCall, ToolPlan
from pet_project_agent.knowledge.base import KnowledgeBase


@dataclass(frozen=True)
class RoutingSignals:
    project_request: bool
    profile_signal: bool
    technical_signal: bool
    subject_signal: bool
    github_signal: bool
    hackernews_signal: bool
    vague_query: bool


class RuleBasedRoutingEngine:
    def __init__(
        self,
        available_tools: list[str] | None = None,
        knowledge_base: KnowledgeBase | None = None,
    ) -> None:
        self.available_tools = set(
            available_tools
            or ["profile_tool", "github_search_tool", "hackernews_search_tool"]
        )
        self.knowledge_base = knowledge_base or KnowledgeBase.default()

    def analyze(self, user_query: str) -> RoutingSignals:
        normalized_query = user_query.lower().strip()
        return RoutingSignals(
            project_request=self._contains_any(normalized_query, self.knowledge_base.routing.project_markers),
            profile_signal=self._needs_profile_tool(normalized_query),
            technical_signal=self._contains_any(normalized_query, self.knowledge_base.routing.technical_markers),
            subject_signal=self._contains_any(normalized_query, self.knowledge_base.routing.subject_markers),
            github_signal=self._needs_github_tool(normalized_query),
            hackernews_signal=self._contains_any(normalized_query, self.knowledge_base.routing.hackernews_markers),
            vague_query=self._contains_any(normalized_query, self.knowledge_base.routing.vague_markers),
        )

    def build_rule_based_plan(self, user_query: str) -> ToolPlan | None:
        normalized_query = user_query.lower().strip()
        if not normalized_query:
            return ToolPlan(
                needs_clarification=True,
                clarification_question="Опишите, пожалуйста, стек, цель проекта и желаемый срок.",
                tool_calls=[],
                reason="Empty query.",
            )

        signals = self.analyze(normalized_query)

        if signals.vague_query and not any(
            [
                signals.profile_signal,
                signals.technical_signal,
                signals.subject_signal,
                signals.github_signal,
                signals.hackernews_signal,
            ]
        ):
            return ToolPlan(
                needs_clarification=True,
                clarification_question="Уточните, пожалуйста, какие технологии вы знаете, какой проектный домен вам интересен и какой срок у проекта.",
                tool_calls=[],
                reason="Rule-based router found the query too vague.",
            )

        if (
            signals.hackernews_signal
            and not signals.project_request
            and not signals.github_signal
            and not signals.profile_signal
        ):
            return ToolPlan(
                needs_clarification=False,
                clarification_question=None,
                tool_calls=self._tool_calls(user_query, ["hackernews_search_tool"]),
                reason="Rule-based routing selected Hacker News only.",
            )

        if signals.project_request and any(
            [
                signals.technical_signal,
                signals.subject_signal,
                signals.profile_signal,
                signals.github_signal,
                signals.hackernews_signal,
            ]
        ):
            tool_names = ["profile_tool"]
            if signals.github_signal:
                tool_names.append("github_search_tool")
            if signals.hackernews_signal:
                tool_names.append("hackernews_search_tool")
            return ToolPlan(
                needs_clarification=False,
                clarification_question=None,
                tool_calls=self._tool_calls(user_query, tool_names),
                reason="Rule-based routing selected a project-idea flow.",
            )

        if signals.profile_signal and any(
            [signals.technical_signal, signals.subject_signal, signals.github_signal]
        ):
            tool_names = ["profile_tool"]
            if signals.github_signal:
                tool_names.append("github_search_tool")
            if signals.hackernews_signal:
                tool_names.append("hackernews_search_tool")
            return ToolPlan(
                needs_clarification=False,
                clarification_question=None,
                tool_calls=self._tool_calls(user_query, tool_names),
                reason="Rule-based routing selected a profile-first flow.",
            )

        if signals.github_signal and (signals.technical_signal or signals.subject_signal):
            return ToolPlan(
                needs_clarification=False,
                clarification_question=None,
                tool_calls=self._tool_calls(user_query, ["github_search_tool"]),
                reason="Rule-based routing selected GitHub research only.",
            )

        if signals.hackernews_signal and (signals.technical_signal or signals.subject_signal):
            return ToolPlan(
                needs_clarification=False,
                clarification_question=None,
                tool_calls=self._tool_calls(user_query, ["hackernews_search_tool"]),
                reason="Rule-based routing selected Hacker News research.",
            )

        return None

    def build_heuristic_plan(self, user_query: str, reason: str) -> ToolPlan | None:
        if not self.can_proceed_without_clarification(user_query):
            return None

        signals = self.analyze(user_query)
        tool_names: list[str] = []

        if signals.profile_signal or signals.project_request or signals.technical_signal:
            tool_names.append("profile_tool")
        if signals.github_signal:
            tool_names.append("github_search_tool")
        if signals.hackernews_signal:
            tool_names.append("hackernews_search_tool")

        tool_calls = self._tool_calls(user_query, tool_names)
        if not tool_calls:
            return None

        return ToolPlan(
            needs_clarification=False,
            clarification_question=None,
            tool_calls=tool_calls,
            reason=reason,
        )

    def find_missing_required_tools(
        self,
        user_query: str,
        needs_clarification: bool,
        tool_calls: list[ToolCall],
    ) -> list[str]:
        if needs_clarification:
            return []

        signals = self.analyze(user_query)
        tool_names = {tool_call.tool_name for tool_call in tool_calls}
        missing_tools: list[str] = []

        if signals.profile_signal and "profile_tool" not in tool_names and "profile_tool" in self.available_tools:
            missing_tools.append("profile_tool")
        if signals.github_signal and "github_search_tool" not in tool_names and "github_search_tool" in self.available_tools:
            missing_tools.append("github_search_tool")

        return missing_tools

    def can_proceed_without_clarification(self, user_query: str) -> bool:
        normalized_query = user_query.lower().strip()
        if len(normalized_query) < 20:
            return False

        signals = self.analyze(normalized_query)

        if signals.vague_query:
            return any(
                [
                    signals.technical_signal,
                    signals.profile_signal,
                    signals.github_signal,
                    signals.hackernews_signal,
                ]
            )

        return (
            (
                signals.project_request
                and any(
                    [
                        signals.technical_signal,
                        signals.profile_signal,
                        signals.github_signal,
                        signals.hackernews_signal,
                        signals.subject_signal,
                    ]
                )
            )
            or signals.github_signal
            or signals.hackernews_signal
        )

    def _needs_profile_tool(self, normalized_query: str) -> bool:
        return (
            self._contains_any(normalized_query, self.knowledge_base.routing.goal_markers)
            or self._contains_any(normalized_query, self.knowledge_base.routing.duration_markers)
            or self._contains_any(normalized_query, self.knowledge_base.routing.level_markers)
            or self._contains_any(normalized_query, self.knowledge_base.routing.profile_phrase_markers)
        )

    def _needs_github_tool(self, normalized_query: str) -> bool:
        if self._contains_any(normalized_query, self.knowledge_base.routing.explicit_research_markers):
            return True

        if (
            self._contains_any(normalized_query, self.knowledge_base.routing.hackernews_markers)
            and not self._contains_any(normalized_query, self.knowledge_base.routing.explicit_research_markers)
            and not self._contains_any(normalized_query, self.knowledge_base.routing.project_markers)
        ):
            return False

        technical_signal_count = sum(
            1 for marker in self.knowledge_base.routing.github_technical_markers if marker in normalized_query
        )
        has_duration = self._contains_any(normalized_query, self.knowledge_base.routing.duration_markers)
        asks_for_project = self._contains_any(normalized_query, self.knowledge_base.routing.project_markers)

        return technical_signal_count >= 2 and (asks_for_project or has_duration)

    def _tool_calls(self, user_query: str, tool_names: list[str]) -> list[ToolCall]:
        unique_tool_names: list[str] = []
        for tool_name in tool_names:
            if tool_name in self.available_tools and tool_name not in unique_tool_names:
                unique_tool_names.append(tool_name)
        return [ToolCall(tool_name=tool_name, query=user_query) for tool_name in unique_tool_names]

    @staticmethod
    def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
        return any(marker in text for marker in markers)

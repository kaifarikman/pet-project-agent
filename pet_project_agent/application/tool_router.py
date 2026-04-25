import json
import re

from pet_project_agent.application.routing_rules import RuleBasedRoutingEngine
from pet_project_agent.domain.models import ToolCall, ToolPlan
from pet_project_agent.domain.ports import LLMClientPort


class ToolRouter:
    def __init__(
        self,
        llm_client: LLMClientPort,
        available_tools: list[str] | None = None,
        routing_mode: str = "rules_first",
        rule_engine: RuleBasedRoutingEngine | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.available_tools = available_tools or [
            "profile_tool",
            "github_search_tool",
            "hackernews_search_tool",
        ]
        self.routing_mode = routing_mode
        self.rule_engine = rule_engine or RuleBasedRoutingEngine(self.available_tools)

    def build_plan(self, user_query: str) -> ToolPlan:
        if self.routing_mode == "rules_only":
            rule_based_plan = self.rule_engine.build_rule_based_plan(user_query)
            if rule_based_plan is not None:
                return rule_based_plan
            heuristic_plan = self.rule_engine.build_heuristic_plan(
                user_query=user_query,
                reason="Rules-only routing used heuristic fallback.",
            )
            if heuristic_plan is not None:
                return heuristic_plan
            return ToolPlan(
                needs_clarification=True,
                clarification_question="Уточните, пожалуйста, технологии, цель проекта и срок.",
                tool_calls=[],
                reason="Rules-only routing could not determine a plan.",
            )

        if self.routing_mode == "rules_first":
            rule_based_plan = self.rule_engine.build_rule_based_plan(user_query)
            if rule_based_plan is not None:
                return rule_based_plan

        prompt = self._build_prompt(user_query)
        try:
            raw_response = self.llm_client.generate(prompt, json_mode=True)
        except RuntimeError:
            heuristic_plan = self.rule_engine.build_heuristic_plan(
                user_query=user_query,
                reason="LLM router is unavailable; used heuristic routing instead.",
            )
            if heuristic_plan is not None:
                return heuristic_plan
            return ToolPlan(
                needs_clarification=True,
                clarification_question="Не удалось обратиться к локальной модели. Уточните, пожалуйста, стек, цель и срок проекта.",
                tool_calls=[],
                reason="LLM router is unavailable.",
            )

        try:
            parsed = self._parse_json(raw_response)
        except ValueError:
            heuristic_plan = self.rule_engine.build_heuristic_plan(
                user_query=user_query,
                reason="Router returned invalid JSON; used heuristic routing instead.",
            )
            if heuristic_plan is not None:
                return heuristic_plan
            return ToolPlan(
                needs_clarification=True,
                clarification_question="Не удалось понять план инструментов. Уточните, пожалуйста, ваш стек, цель и желаемый тип проекта.",
                tool_calls=[],
                reason="Router returned invalid JSON.",
            )

        needs_clarification = bool(parsed.get("needs_clarification"))
        clarification_question = parsed.get("clarification_question")
        reason = str(parsed.get("reason") or "").strip()
        tool_calls = self._parse_tool_calls(parsed.get("tool_calls"))

        if self.routing_mode == "llm_first":
            missing_required_tools = self.rule_engine.find_missing_required_tools(
                user_query=user_query,
                needs_clarification=needs_clarification,
                tool_calls=tool_calls,
            )
            if missing_required_tools:
                repaired_plan = self._repair_plan(user_query, missing_required_tools)
                if repaired_plan is not None:
                    return repaired_plan
                tool_calls = self._append_required_tools(
                    user_query=user_query,
                    tool_calls=tool_calls,
                    missing_tools=missing_required_tools,
                )
                reason = self._append_reason(
                    reason,
                    f"Validated and completed required tools: {', '.join(missing_required_tools)}.",
                )

            if needs_clarification:
                heuristic_plan = self.rule_engine.build_heuristic_plan(
                    user_query=user_query,
                    reason=reason or "LLM requested clarification, but heuristic routing found enough signal to proceed.",
                )
                if heuristic_plan is not None:
                    return heuristic_plan
                return ToolPlan(
                    needs_clarification=True,
                    clarification_question=clarification_question
                    or "Уточните, пожалуйста, технологии, цель проекта и срок.",
                    tool_calls=[],
                    reason=reason or "Not enough information for research.",
                )

            if not tool_calls:
                return ToolPlan(
                    needs_clarification=True,
                    clarification_question="Уточните, пожалуйста, технологии, цель проекта и срок.",
                    tool_calls=[],
                    reason=reason or "No valid tool calls were produced.",
                )

            return ToolPlan(
                needs_clarification=False,
                clarification_question=None,
                tool_calls=tool_calls,
                reason=reason,
            )

        if needs_clarification:
            heuristic_plan = self.rule_engine.build_heuristic_plan(
                user_query=user_query,
                reason=reason or "LLM requested clarification, but heuristic routing found enough signal to proceed.",
            )
            if heuristic_plan is not None:
                return heuristic_plan

        missing_required_tools = self.rule_engine.find_missing_required_tools(
            user_query=user_query,
            needs_clarification=needs_clarification,
            tool_calls=tool_calls,
        )

        if missing_required_tools:
            repaired_plan = self._repair_plan(user_query, missing_required_tools)
            if repaired_plan is not None:
                return repaired_plan
            tool_calls = self._append_required_tools(
                user_query=user_query,
                tool_calls=tool_calls,
                missing_tools=missing_required_tools,
            )
            reason = self._append_reason(
                reason,
                f"Validated and completed required tools: {', '.join(missing_required_tools)}.",
            )

        if needs_clarification:
            return ToolPlan(
                needs_clarification=True,
                clarification_question=clarification_question
                or "Уточните, пожалуйста, технологии, цель проекта и срок.",
                tool_calls=[],
                reason=reason or "Not enough information for research.",
            )

        if not tool_calls:
            return ToolPlan(
                needs_clarification=True,
                clarification_question="Уточните, пожалуйста, технологии, цель проекта и срок.",
                tool_calls=[],
                reason=reason or "No valid tool calls were produced.",
            )

        return ToolPlan(
            needs_clarification=False,
            clarification_question=None,
            tool_calls=tool_calls,
            reason=reason,
        )

    def _build_prompt(self, user_query: str) -> str:
        available_tools = "\n".join(f"- {tool_name}" for tool_name in self.available_tools)

        return f"""
You are a tool router for a CLI AI agent that suggests portfolio pet-project ideas.

Available tools:
{available_tools}

Routing rules:
- You MUST use profile_tool when the user provides any information about skills, goal, timeline, or experience.
- You MUST use github_search_tool when the user asks for real open-source examples, repositories, or GitHub research.
- Use hackernews_search_tool only when trends, discussions, or extra market signal would help.
- Do not call every tool automatically.
- If the query is too vague, ask for clarification instead of inventing research.
- Prefer proceeding with profile_tool when the user already described a project direction, stack, or implementation preference, even if some details are missing.
- Only ask clarification when there is not enough information to produce even a first-pass idea shortlist.
- Return strict JSON only, with no markdown and no explanation outside JSON.

Examples:
- Query: "Я знаю Python, FastAPI, SQL. Хочу проект для портфолио за 2 недели. Найди реальные open-source примеры."
  Required tools: profile_tool, github_search_tool
- Query: "Хочу написать пет-проект с агентной системой, пишу в основном на Python."
  Required tools: profile_tool
- Query: "Хочу какой-нибудь проект"
  Return needs_clarification=true and no tools.

Expected JSON schema:
{{
  "needs_clarification": false,
  "clarification_question": null,
  "tool_calls": [
    {{
      "tool_name": "profile_tool",
      "query": "..."
    }}
  ],
  "reason": "..."
}}

User query:
{user_query}
""".strip()

    def _parse_tool_calls(self, raw_tool_calls: object) -> list[ToolCall]:
        if not isinstance(raw_tool_calls, list):
            return []

        parsed_calls: list[ToolCall] = []

        for item in raw_tool_calls:
            if not isinstance(item, dict):
                continue

            tool_name = str(item.get("tool_name") or "").strip()
            query = str(item.get("query") or "").strip()

            if tool_name not in self.available_tools or not query:
                continue

            parsed_calls.append(ToolCall(tool_name=tool_name, query=query))

        return parsed_calls

    def _parse_json(self, raw_response: str) -> dict:
        candidate = raw_response.strip()

        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, re.DOTALL)
        if fence_match:
            candidate = fence_match.group(1)
        elif not candidate.startswith("{"):
            candidate = self._extract_json_object(candidate)

        parsed = json.loads(candidate)
        if not isinstance(parsed, dict):
            raise ValueError("Router response is not a JSON object.")
        return parsed

    def _repair_plan(self, user_query: str, missing_tools: list[str]) -> ToolPlan | None:
        repair_prompt = f"""
You returned a tool plan that missed required tools.

User query:
{user_query}

Missing tools that must be considered:
{missing_tools}

Return corrected JSON only.
Use profile_tool whenever the query already contains skills, goal, or timeline.
Use github_search_tool whenever the query explicitly asks for real open-source examples, repositories, or GitHub research.
Keep the same JSON schema as before.
""".strip()

        try:
            repaired_raw_response = self.llm_client.generate(repair_prompt, json_mode=True)
            repaired = self._parse_json(repaired_raw_response)
        except (RuntimeError, ValueError):
            return None

        repaired_tool_calls = self._parse_tool_calls(repaired.get("tool_calls"))

        if self.rule_engine.find_missing_required_tools(
            user_query=user_query,
            needs_clarification=bool(repaired.get("needs_clarification")),
            tool_calls=repaired_tool_calls,
        ):
            return None

        return ToolPlan(
            needs_clarification=bool(repaired.get("needs_clarification")),
            clarification_question=repaired.get("clarification_question"),
            tool_calls=[] if repaired.get("needs_clarification") else repaired_tool_calls,
            reason=str(repaired.get("reason") or "").strip(),
        )

    @staticmethod
    def _extract_json_object(text: str) -> str:
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON object found.")

        depth = 0

        for index in range(start, len(text)):
            char = text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:index + 1]

        raise ValueError("Unbalanced JSON object.")

    @staticmethod
    def _append_required_tools(
        user_query: str,
        tool_calls: list[ToolCall],
        missing_tools: list[str],
    ) -> list[ToolCall]:
        completed_tool_calls = list(tool_calls)
        existing_tool_names = {tool_call.tool_name for tool_call in completed_tool_calls}

        for tool_name in missing_tools:
            if tool_name in existing_tool_names:
                continue
            tool_call = ToolCall(tool_name=tool_name, query=user_query)
            if tool_name == "profile_tool":
                completed_tool_calls.insert(0, tool_call)
            else:
                completed_tool_calls.append(tool_call)
            existing_tool_names.add(tool_name)

        return completed_tool_calls

    @staticmethod
    def _append_reason(reason: str, suffix: str) -> str:
        if not reason:
            return suffix
        return f"{reason} {suffix}"

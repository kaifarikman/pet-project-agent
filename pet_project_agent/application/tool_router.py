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
Вы — маршрутизатор инструментов для CLI-агента, который предлагает идеи пет-проектов.

Доступные инструменты:
{available_tools}

Правила маршрутизации:
- Вы ДОЛЖНЫ использовать profile_tool, если пользователь предоставляет любую информацию о навыках, целях, сроках или опыте.
- Вы ДОЛЖНЫ использовать github_search_tool, если пользователь запрашивает реальные примеры с открытым исходным кодом, репозитории или исследование GitHub.
- Используйте hackernews_search_tool только тогда, когда тренды, обсуждения или дополнительные рыночные сигналы могут помочь.
- Не вызывайте все инструменты автоматически.
- Если запрос слишком расплывчатый, запросите уточнение вместо того, чтобы выдумывать исследование.
- Предпочитайте использование profile_tool, когда пользователь уже описал направление проекта, стек или предпочтения по реализации, даже если некоторые детали отсутствуют.
- Запрашивайте уточнение только тогда, когда информации недостаточно даже для составления первого списка идей.
- Возвращайте только строгий JSON, без markdown и пояснений вне JSON.
- ВАЖНО: поле `clarification_question` ДОЛЖНО быть на русском языке.

Примеры:
- Запрос: "Я знаю Python, FastAPI, SQL. Хочу проект для портфолио за 2 недели. Найди реальные open-source примеры."
  Необходимые инструменты: profile_tool, github_search_tool
- Запрос: "Хочу написать пет-проект с агентной системой, пишу в основном на Python."
  Необходимые инструменты: profile_tool
- Запрос: "Хочу какой-нибудь проект"
  Вернуть needs_clarification=true и пустой список инструментов.

Ожидаемая схема JSON:
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

Запрос пользователя:
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
Вы вернули план инструментов, в котором отсутствуют необходимые инструменты.

Запрос пользователя:
{user_query}

Недостающие инструменты, которые необходимо рассмотреть:
{missing_tools}

Верните только исправленный JSON.
Используйте profile_tool всегда, когда запрос уже содержит навыки, цель или сроки.
Используйте github_search_tool всегда, когда в запросе явно запрашиваются реальные примеры с открытым исходным кодом, репозитории или исследования GitHub.
Соблюдайте ту же схему JSON, что и раньше.
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

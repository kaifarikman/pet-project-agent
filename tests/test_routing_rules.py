from pet_project_agent.application.routing_rules import RuleBasedRoutingEngine


def test_rule_engine_routes_project_query_without_clarification() -> None:
    engine = RuleBasedRoutingEngine()

    plan = engine.build_rule_based_plan(
        "хочу написать пет-проект с агентной системой. предложи варианты. пишу в основном на питоне"
    )

    assert plan is not None
    assert plan.needs_clarification is False
    assert [tool_call.tool_name for tool_call in plan.tool_calls] == ["profile_tool"]


def test_rule_engine_keeps_hackernews_only_flow() -> None:
    engine = RuleBasedRoutingEngine()

    plan = engine.build_rule_based_plan(
        "посмотри, что обсуждают на hacker news про fastapi"
    )

    assert plan is not None
    assert plan.needs_clarification is False
    assert [tool_call.tool_name for tool_call in plan.tool_calls] == [
        "hackernews_search_tool"
    ]


def test_rule_engine_requests_clarification_for_vague_query() -> None:
    engine = RuleBasedRoutingEngine()

    plan = engine.build_rule_based_plan("хочу какой-нибудь проект")

    assert plan is not None
    assert plan.needs_clarification is True
    assert plan.tool_calls == []


def test_rule_engine_routes_github_research_query() -> None:
    engine = RuleBasedRoutingEngine()

    plan = engine.build_rule_based_plan(
        "найди реальные open-source примеры fastapi sql проекта"
    )

    assert plan is not None
    assert plan.needs_clarification is False
    assert [tool_call.tool_name for tool_call in plan.tool_calls] == [
        "profile_tool",
        "github_search_tool",
    ]

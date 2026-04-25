from pet_project_agent.application.tool_router import ToolRouter


class FailingLLM:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str, json_mode: bool = False) -> str:
        self.calls += 1
        raise AssertionError("LLM should not be called for rule-based route")


def test_tool_router_uses_rule_engine_before_llm() -> None:
    llm = FailingLLM()
    router = ToolRouter(llm)

    plan = router.build_plan(
        "хочу написать такой пет проект, в котором можно будет добавить агентную систему. пишу в основном на питоне"
    )

    assert plan.needs_clarification is False
    assert [tool_call.tool_name for tool_call in plan.tool_calls] == ["profile_tool"]
    assert llm.calls == 0

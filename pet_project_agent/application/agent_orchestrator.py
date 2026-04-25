from pet_project_agent.contexts.ideation.service import IdeationService
from pet_project_agent.application.response_renderer import ResponseRenderer


class AgentOrchestrator:
    def __init__(
        self,
        tool_router,
        tool_executor,
        ideation_service: IdeationService,
        response_renderer: ResponseRenderer,
    ) -> None:
        self.tool_router = tool_router
        self.tool_executor = tool_executor
        self.ideation_service = ideation_service
        self.response_renderer = response_renderer

    def run(self, user_query: str, include_debug: bool = False) -> str:
        tool_plan = self.tool_router.build_plan(user_query)

        if tool_plan.needs_clarification:
            return tool_plan.clarification_question or "Нужно больше деталей о вашем стеке, цели и сроке."

        research_result = self.tool_executor.execute(tool_plan)
        ideas = self.ideation_service.generate_ideas(research_result)
        return self.response_renderer.render(
            research_result,
            ideas,
            include_debug=include_debug,
        )

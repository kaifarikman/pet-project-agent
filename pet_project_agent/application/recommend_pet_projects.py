class RecommendPetProjectsUseCase:
    def __init__(self, orchestrator) -> None:
        self.orchestrator = orchestrator

    def execute(self, user_query: str, include_debug: bool = False) -> str:
        return self.orchestrator.run(user_query, include_debug=include_debug)

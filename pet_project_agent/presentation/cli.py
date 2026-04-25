import sys
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.theme import Theme

from pet_project_agent.application.agent_orchestrator import AgentOrchestrator
from pet_project_agent.application.recommend_pet_projects import (
    RecommendPetProjectsUseCase,
)
from pet_project_agent.application.response_renderer import ResponseRenderer
from pet_project_agent.application.routing_rules import RuleBasedRoutingEngine
from pet_project_agent.application.tool_executor import ToolExecutor
from pet_project_agent.application.tool_router import ToolRouter
from pet_project_agent.contexts.github_research.tool import GitHubSearchTool
from pet_project_agent.contexts.hn_research.tool import HackerNewsSearchTool
from pet_project_agent.contexts.ideation.service import IdeationService
from pet_project_agent.contexts.profile.service import ProfileService
from pet_project_agent.contexts.profile.tool import ProfileTool
from pet_project_agent.infrastructure.data.skill_catalog_repository import (
    SkillCatalogRepository,
)
from pet_project_agent.infrastructure.github.client import GitHubClient
from pet_project_agent.infrastructure.hackernews.client import HackerNewsClient
from pet_project_agent.infrastructure.llm.ollama_client import OllamaClient
from pet_project_agent.knowledge.base import KnowledgeBase
from pet_project_agent.settings import AppSettings

# Настройка темы Rich
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "section": "bold cyan",
    "agent": "bold blue"
})

console = Console(theme=custom_theme)
app = typer.Typer(
    help="AI-агент для поиска идей пет-проектов.", 
    add_completion=False,
    invoke_without_command=True
)

def _build_use_case() -> RecommendPetProjectsUseCase:
    settings = AppSettings.from_env()
    knowledge_base = KnowledgeBase.default()
    skill_catalog_repository = SkillCatalogRepository(settings.skill_catalog_path)
    
    llm_client = OllamaClient()
    
    profile_tool = ProfileTool(
        skill_catalog_repository=skill_catalog_repository,
        service=ProfileService(knowledge_base=knowledge_base),
    )
    github_tool = GitHubSearchTool(
        client=GitHubClient(),
        limit=10,
        min_stars=settings.github_min_stars,
        skill_catalog_repository=skill_catalog_repository,
        profile_service=ProfileService(knowledge_base=knowledge_base),
        llm_client=llm_client,
    )
    hn_tool = HackerNewsSearchTool(
        client=HackerNewsClient(),
        limit=settings.hackernews_search_limit,
    )

    tool_router = ToolRouter(
        llm_client=llm_client,
        routing_mode=settings.routing_mode,
        rule_engine=RuleBasedRoutingEngine(
            available_tools=[profile_tool.name, github_tool.name, hn_tool.name],
            knowledge_base=knowledge_base,
        ),
    )
    tool_executor = ToolExecutor(
        tools={
            profile_tool.name: profile_tool,
            github_tool.name: github_tool,
            hn_tool.name: hn_tool,
        }
    )
    orchestrator = AgentOrchestrator(
        tool_router=tool_router,
        tool_executor=tool_executor,
        ideation_service=IdeationService(llm_client=llm_client),
        response_renderer=ResponseRenderer(),
    )
    return RecommendPetProjectsUseCase(orchestrator=orchestrator)

def _execute_and_print(use_case: RecommendPetProjectsUseCase, query: str, debug: bool):
    with console.status("[bold blue]Агент думает...[/bold blue]"):
        try:
            response = use_case.execute(query, include_debug=debug)
            console.print(f"\n[bold blue]✦[/bold blue] [bold white]агент[/bold white]")
            console.print(Markdown(response))
        except Exception as e:
            console.print(f"[error]Ошибка: {e}[/error]")

def _print_welcome():
    console.print(Panel(
        "[bold cyan]pet-project-agent[/bold cyan]\n"
        "[dim]Напишите стек, цель и срок. Я предложу 3 идеи проектов.[/dim]\n"
        "[dim]Команды: [bold]debug[/bold], [bold]exit[/bold].[/dim]",
        border_style="blue"
    ))

@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    query: Optional[str] = typer.Argument(None, help="Ваш запрос (стек, цели, срок)"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Включить отладочную информацию")
):
    """AI-агент для поиска идей пет-проектов."""
    if ctx.invoked_subcommand is None:
        chat(query=query, debug=debug)

@app.command()
def chat(
    query: Optional[str] = typer.Argument(None, help="Ваш запрос (стек, цели, срок)"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Включить отладочную информацию")
):
    """Запустить интерактивную сессию или выполнить одиночный запрос."""
    use_case = _build_use_case()

    if query:
        _execute_and_print(use_case, query, debug)
        return

    _print_welcome()
    
    while True:
        user_input = Prompt.ask("\n[bold cyan]➜[/bold cyan] [bold white]вы[/bold white]").strip()

        if user_input.lower() in {"exit", "quit", "q", "выход"}:
            console.print("[info]Сессия завершена. До встречи![/info]")
            raise typer.Exit()
        
        if user_input.lower() == "debug":
            debug = not debug
            console.print(f"[info]Debug mode: {'ON' if debug else 'OFF'}[/info]")
            continue

        if not user_input:
            continue

        _execute_and_print(use_case, user_input, debug)

@app.command()
def how():
    """Как это работает?"""
    text = """
1. **Вы описываете себя**: стек, опыт, цели и желаемый срок.
2. **Агент строит профиль**: анализирует ваши навыки и домены.
3. **Исследование**: агент ищет релевантные проекты на GitHub и тренды на Hacker News.
4. **Генерация**: LLM создает 3 уникальные идеи с MVP-фичами и ссылками.
    """
    console.print(Panel(Markdown(text), title="[section]Механика работы[/section]", expand=False))

def main():
    app()

if __name__ == "__main__":
    main()

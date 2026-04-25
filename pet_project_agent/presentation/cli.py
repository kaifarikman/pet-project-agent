import sys
import textwrap

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

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
BLUE = "\033[34m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"

SECTION_TITLES = {
    "Топ-3 pet-проекта",
    "Какие инструменты и источники использованы",
    "Ограничения",
}
EXIT_COMMANDS = {"exit", "quit", "q", "выход"}
HELP_COMMANDS = {"help", "/help", "помощь"}
EXAMPLE_COMMANDS = {"examples", "/examples", "примеры"}
HOW_COMMANDS = {"how", "/how", "как", "что ты умеешь"}
DEBUG_COMMANDS = {"debug", "/debug"}


def run_cli() -> None:
    use_case = _build_use_case(AppSettings.from_env())
    cli_query = " ".join(sys.argv[1:]).strip()

    if cli_query:
        _run_single_query(use_case, cli_query)
        return

    _run_interactive_session(use_case)


def _run_single_query(use_case: RecommendPetProjectsUseCase, query: str) -> None:
    if not query:
        _print_warning("Пустой запрос. Опишите ваш стек, цель и желаемый срок проекта.")
        return

    try:
        response = use_case.execute(query, include_debug=False)
    except RuntimeError as error:
        _print_error(str(error))
        return

    _print_response(response)


def _run_interactive_session(use_case: RecommendPetProjectsUseCase) -> None:
    _print_welcome()
    debug_mode = False

    while True:
        try:
            query = input(f"{BOLD}{CYAN}you>{RESET} ").strip()
        except EOFError:
            print()
            _print_info("Сессия завершена.")
            return
        except KeyboardInterrupt:
            print()
            _print_info("Сессия прервана.")
            return

        if not query:
            _print_warning("Пустой запрос. Опишите стек, цель, срок и желаемый тип проекта.")
            continue

        if query.lower() in EXIT_COMMANDS:
            _print_info("До встречи.")
            return
        if query.lower() in DEBUG_COMMANDS:
            debug_mode = not debug_mode
            state = "включён" if debug_mode else "выключен"
            _print_info(f"Debug-режим {state}.")
            print()
            continue
        if query.lower() in HELP_COMMANDS:
            _print_help()
            print()
            continue
        if query.lower() in EXAMPLE_COMMANDS:
            _print_examples()
            print()
            continue
        if query.lower() in HOW_COMMANDS:
            _print_how_it_works()
            print()
            continue

        print(f"\n{BOLD}{BLUE}agent>{RESET}")
        try:
            response = use_case.execute(query, include_debug=debug_mode)
        except RuntimeError as error:
            _print_error(str(error))
            print()
            continue

        _print_response(response)
        print()


def _build_use_case(settings: AppSettings) -> RecommendPetProjectsUseCase:
    knowledge_base = KnowledgeBase.default()
    skill_catalog_repository = SkillCatalogRepository(settings.skill_catalog_path)
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
    )
    hn_tool = HackerNewsSearchTool(
        client=HackerNewsClient(),
        limit=settings.hackernews_search_limit,
    )
    llm_client = OllamaClient()

    tool_router = ToolRouter(
        llm_client=llm_client,
        routing_mode=settings.routing_mode,
        rule_engine=RuleBasedRoutingEngine(
            available_tools=[
                profile_tool.name,
                github_tool.name,
                hn_tool.name,
            ],
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


def _print_welcome() -> None:
    print(f"{BOLD}{CYAN}pet-project-agent{RESET}")
    print(
        f"{DIM}Напишите, что вы умеете, на чём пишете, какой проект хотите и на какой срок."
        f" На выходе вы получите 3 идеи pet-проектов.{RESET}"
    )
    print(
        f"{DIM}Команды: help, examples, how, debug, exit.{RESET}"
    )
    print()


def _print_help() -> None:
    print(f"{BOLD}{CYAN}Как пользоваться{RESET}")
    _print_wrapped(
        "Опишите стек, цель, срок и желаемый тип проекта. Чем конкретнее запрос, тем лучше будут идеи."
    )
    _print_wrapped(
        "Лучший формат: технологии + цель + срок + интересный домен или тип проекта."
    )
    print()
    _print_wrapped("Пример: Я знаю Python, FastAPI и SQL. Хочу pet-проект для портфолио на 2-3 недели.")
    _print_wrapped("Если нужны служебные детали про tools и research, включите команду `debug`.")


def _print_examples() -> None:
    print(f"{BOLD}{CYAN}Примеры запросов{RESET}")
    examples = [
        "Я знаю Python, FastAPI и SQL. Хочу проект для портфолио на 2 недели.",
        "Пишу в основном на Python и pandas. Хочу data-проект для стажировки.",
        "Хочу pet-проект с агентной системой, пишу на Python.",
        "Найди реальные open-source примеры FastAPI-проектов для портфолио.",
    ]
    for example in examples:
        _print_wrapped(f"• {example}", indent="  ", subsequent_indent="    ")


def _print_how_it_works() -> None:
    print(f"{BOLD}{CYAN}Как это работает{RESET}")
    _print_wrapped(
        "1. Вы пишете, что умеете, на чём пишете, какую цель преследуете и какой срок у проекта."
    )
    _print_wrapped(
        "2. Агент строит профиль: стек, домены, цель, срок и уровень конкретности запроса."
    )
    _print_wrapped(
        "3. При необходимости агент вызывает tools: локальный каталог навыков, GitHub research, Hacker News research."
    )
    _print_wrapped(
        "4. На выходе агент даёт 3 идеи pet-проектов с MVP-фичами, стеком и, если есть, реальными references."
    )


def _print_response(response: str) -> None:
    lines = response.splitlines()

    for line in lines:
        stripped = line.strip()

        if not stripped:
            print()
            continue

        if stripped in SECTION_TITLES:
            print(f"{BOLD}{CYAN}{stripped}{RESET}")
            continue

        if stripped == "MVP features:":
            print(f"{BOLD}{GREEN}MVP features{RESET}")
            continue

        if stripped == "GitHub references:":
            print(f"{BOLD}{GREEN}GitHub references{RESET}")
            continue

        if stripped.startswith("- "):
            _print_wrapped(f"• {stripped[2:]}", indent="  ", subsequent_indent="    ")
            continue

        if _is_numbered_item(stripped):
            number, _, content = stripped.partition(". ")
            print(f"{BOLD}{YELLOW}{number}.{RESET} {content}")
            continue

        _print_wrapped(stripped)


def _print_wrapped(text: str, indent: str = "", subsequent_indent: str | None = None) -> None:
    wrapped = textwrap.fill(
        text,
        width=96,
        initial_indent=indent,
        subsequent_indent=subsequent_indent or indent,
        break_long_words=False,
        break_on_hyphens=False,
    )
    print(wrapped)


def _print_warning(message: str) -> None:
    print(f"{YELLOW}{message}{RESET}")


def _print_error(message: str) -> None:
    print(f"{RED}Ошибка: {message}{RESET}")


def _print_info(message: str) -> None:
    print(f"{DIM}{message}{RESET}")


def _is_numbered_item(text: str) -> bool:
    number, separator, _ = text.partition(". ")
    return bool(separator) and number.isdigit()

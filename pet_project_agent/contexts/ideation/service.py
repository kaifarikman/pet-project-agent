import json
import logging
from typing import List, Any

from pet_project_agent.domain.models import ProjectIdea, ResearchResult
from pet_project_agent.domain.ports import LLMClientPort

logger = logging.getLogger(__name__)

class IdeationService:
    def __init__(self, llm_client: LLMClientPort = None) -> None:
        self.llm_client = llm_client

    def generate_ideas(self, research_result: ResearchResult) -> List[ProjectIdea]:
        if self.llm_client is None:
            return self._get_fallback_ideas(research_result, "LLM client is not configured.")

        # Собираем список всех РЕАЛЬНО найденных URL для валидации
        valid_urls = {repo.url for repo in research_result.github_repositories}

        prompt = self._build_prompt(research_result)
        try:
            raw_response = self.llm_client.generate(prompt, json_mode=True)
            ideas_data = self._parse_flexible_json(raw_response)
            
            if not ideas_data:
                raise ValueError("Could not extract a list of ideas from LLM response.")

            ideas = []
            for item in ideas_data[:3]:
                # Валидация ссылок: оставляем только те, что были в поиске
                raw_refs = item.get("references") if isinstance(item.get("references"), list) else []
                validated_refs = [url for url in raw_refs if url in valid_urls]

                ideas.append(
                    ProjectIdea(
                        title=item.get("title") or item.get("name") or "Интересный проект",
                        description=item.get("description") or "Описание в разработке",
                        stack=item.get("stack") if isinstance(item.get("stack"), list) else [],
                        mvp_features=item.get("mvp_features") if isinstance(item.get("mvp_features"), list) else [],
                        why_it_fits=item.get("why_it_fits") or "Подходит под ваш стек и интересы.",
                        references=validated_refs
                    )
                )
            
            if not ideas:
                return self._get_fallback_ideas(research_result, "LLM returned empty list.")
                
            return ideas

        except Exception as e:
            logger.error(f"Failed to generate ideas via LLM: {e}")
            return self._get_fallback_ideas(research_result, f"Error: {e}")

    def _parse_flexible_json(self, raw_response: str) -> List[Any]:
        """Пытается найти список идей в JSON ответе любым способом."""
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError:
            return []

        # 1. Если это сразу список
        if isinstance(data, list):
            return data
        
        # 2. Если это словарь, ищем список в известных ключах
        if isinstance(data, dict):
            for key in ["ideas", "projects", "result", "suggestions", "items"]:
                if isinstance(data.get(key), list):
                    return data[key]
            
            # 3. Если ничего не нашли, но в словаре есть только один ключ и там список
            lists_in_dict = [v for v in data.values() if isinstance(v, list)]
            if len(lists_in_dict) == 1:
                return lists_in_dict[0]
                
            # 4. Если сам словарь похож на одну идею, оборачиваем в список
            if "title" in data or "description" in data:
                return [data]

        return []

    def _build_prompt(self, research_result: ResearchResult) -> str:
        profile = research_result.user_profile
        skills = ", ".join(profile.skills) if profile and profile.skills else "не указаны"
        domains = ", ".join(profile.domains) if profile and profile.domains else "не указаны"
        goal = profile.goal if profile else "не указана"
        
        repo_context = ""
        if research_result.github_repositories:
            repo_context = "Список найденных РЕАЛЬНЫХ репозиториев на GitHub для вдохновения (ссылка и описание):\n"
            for repo in research_result.github_repositories[:10]:
                repo_context += f"- {repo.url} | Описание: {repo.description}\n"

        hn_context = ""
        if research_result.hackernews_items:
            hn_context = "Тренды с Hacker News:\n"
            for item in research_result.hackernews_items[:3]:
                hn_context += f"- {item.title} ({item.url})\n"

        return f"""
Вы — эксперт по карьере в IT. Ваша задача: предложить 3 идеи ПОРТФОЛИО-проектов (pet-projects) для разработчика.

ОТВЕЧАЙ СТРОГО НА РУССКОМ ЯЗЫКЕ.

Данные пользователя:
- Навыки: {skills}
- Интересы: {domains}
- Цель: {goal}
- Запрос пользователя: {profile.raw_text if profile else "неизвестен"}

Контекст из поиска (используй эти ссылки в references):
{repo_context if repo_context else "Реальных примеров на GitHub не найдено."}
{hn_context}

Инструкции по генерации:
1. Предложите 3 разных идеи проектов, максимально использующих навыки пользователя.
2. Для каждой идеи ОБЯЗАТЕЛЬНО найди в "Контексте" репозиторий, который может служить ПРАКТИЧЕСКИМ ПРИМЕРОМ или образцом кода для реализации этой идеи. 
3. Ссылка в `references` должна помогать пользователю понять, как устроена архитектура или конкретные фичи подобного проекта.
4. Если репозиторий из контекста слишком сложный или не подходит — лучше оставить список пустым, чем давать бесполезную ссылку.
5. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО придумывать ссылки, которых нет в "Контексте". 
6. Ответ должен быть в формате JSON с ключом "ideas".

JSON Schema:
{{
  "ideas": [
    {{
      "title": "Название проекта на русском",
      "description": "Суть проекта на русском",
      "stack": ["Технология 1", "Технология 2"],
      "mvp_features": ["фича 1", "фича 2"],
      "why_it_fits": "Почему это круто для портфолио",
      "references": ["ссылка из контекста"]
    }}
  ]
}}
""".strip()

    def _get_fallback_ideas(self, research_result: ResearchResult, reason: str) -> List[ProjectIdea]:
        profile = research_result.user_profile
        stack = profile.skills[:5] if profile and profile.skills else ["python"]
        references = [repo.url for repo in research_result.github_repositories[:3]]

        return [
            ProjectIdea(
                title="Сервис для управления личными задачами",
                description="Небольшой продукт с понятной бизнес-логикой: задачи, статусы, сроки и простая аналитика выполнения.",
                stack=stack,
                mvp_features=["CRUD для задач", "Фильтры по статусам и срокам", "Хранение данных"],
                why_it_fits=f"Система в безопасном режиме. Причина: {reason}",
                references=references[:1],
            ),
            ProjectIdea(
                title="CLI-ассистент для ежедневной рутины",
                description="Инструмент, который помогает автоматизировать повторяющиеся действия: заметки, чек-листы, поиск и короткие отчеты.",
                stack=stack,
                mvp_features=["CLI-команды", "Локальное хранилище", "Экспорт результата в Markdown"],
                why_it_fits=f"Идея не зависит от внешней LLM-генерации и хорошо показывает прикладную автоматизацию. Причина fallback: {reason}",
                references=references[1:2],
            ),
            ProjectIdea(
                title="Мини-дашборд для анализа данных",
                description="Приложение, которое загружает небольшой датасет, считает ключевые метрики и показывает понятный отчет.",
                stack=stack,
                mvp_features=["Импорт CSV", "Расчет метрик", "Отчет или простой веб-интерфейс"],
                why_it_fits=f"Проект легко ограничить по объему и довести до законченного портфолио-результата. Причина fallback: {reason}",
                references=references[2:3],
            ),
        ]

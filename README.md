Track: A+C

`pet-project-agent` is a CLI AI agent that analyzes a user request, decides which tools to call, and proposes realistic portfolio pet-project ideas.

Setup:
`uv sync`

Run:
`uv run pet-project-agent`

Before the first run:
`ollama pull llama3.2`

Environment:
- copy `.env.example` to `.env`
- set `OLLAMA_BASE_URL` and `OLLAMA_MODEL`
- optionally set `GITHUB_TOKEN`
- optionally set `SKILL_CATALOG_PATH`
- optionally set `ROUTING_MODE` to `rules_first`, `llm_first`, or `rules_only`

from dotenv import load_dotenv

from pet_project_agent.presentation.cli import run_cli


def main() -> None:
    load_dotenv()
    run_cli()


if __name__ == "__main__":
    main()

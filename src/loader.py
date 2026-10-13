import json
import sys
from pathlib import Path

from pydantic import ValidationError

from src.models import FunctionDefinition, TestPrompt


def load_function_definitions(path: Path) -> list[FunctionDefinition]:
    """Load and validate function definitions from a JSON file."""
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
            functions = [
                FunctionDefinition(**item)
                for item in data
            ]
            return functions

    except ValidationError as e:
        print(f"Error loading function definitions from {path}: {e}")
        sys.exit(0)

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {path}: {e}")
        sys.exit(0)

    except FileNotFoundError:
        print(f"File not found: {path}")
        sys.exit(0)

    except Exception as e:
        print(
            f"An unexpected error occurred "
            f"while loading function definitions from {path}: {e}"
        )
        sys.exit(0)


def load_test_prompts(path: Path) -> list[TestPrompt]:
    """Load and validate test prompts from a JSON file."""
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

            test_prompts = [
                TestPrompt(**item)
                for item in data
            ]
            return test_prompts

    except ValidationError as e:
        print(f"Error loading test prompts from {path}: {e}")
        sys.exit(0)

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {path}: {e}")
        sys.exit(0)

    except FileNotFoundError:
        print(f"File not found: {path}")
        sys.exit(0)

    except Exception as e:
        print(
            f"An unexpected error occurred "
            f"while loading test prompts from {path}: {e}"
        )
        sys.exit(0)

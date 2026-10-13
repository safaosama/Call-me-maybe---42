import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from llm_sdk import Small_LLM_Model

from pydantic import ValidationError

from src.loader import load_function_definitions, load_test_prompts
from src.models import FunctionCallResult
from src.pipeline import generate_function_call
from src.vocab import Vocab


DEFAULT_FUNCTIONS_DEFINITION = Path("data/input/functions_definition.json")
DEFAULT_INPUT = Path("data/input/function_calling_tests.json")
DEFAULT_OUTPUT = Path("data/output/function_calling_results.json")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(prog="src")
    parser.add_argument(
        "--functions_definition",
        type=Path,
        default=DEFAULT_FUNCTIONS_DEFINITION,
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    """Run the function calling program."""

    args = parse_args()

    functions = load_function_definitions(args.functions_definition)
    prompts = load_test_prompts(args.input)

    if not functions:
        print(
            "Error: no function definitions found in "
            f"{args.functions_definition}"
        )
        sys.exit(0)
    if not prompts:
        print(f"Error: no test prompts found in {args.input}")
        sys.exit(0)

    model = Small_LLM_Model()
    vocab = Vocab(model.get_path_to_vocab_file())
    print(f"Vocab loaded: {vocab.size} tokens")

    function_by_name = {f.name: f for f in functions}
    results = []
    start_time = time.monotonic()
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for i, test_prompt in enumerate(prompts, start=1):
        print(
            f"[{i}/{len(prompts)}] generating for: "
            f"{test_prompt.prompt!r}"
        )
        raw_result = generate_function_call(
            model, vocab, test_prompt.prompt, functions
        )

        try:
            validated = FunctionCallResult(**raw_result)
        except ValidationError as e:
            print(f"  WARNING: output failed schema validation, skipping: {e}")
            continue
        if validated.name == "fn_nomatched":
            print("  ->", validated.model_dump())
            results.append(validated.model_dump())
            continue

        func = function_by_name.get(validated.name)
        if func is None:
            print(
                "  WARNING: unknown function name "
                f"{validated.name!r}, skipping"
            )
            continue

        expected_keys = set(func.parameters.keys())
        actual_keys = set(validated.parameters.keys())
        if expected_keys != actual_keys:
            print(
                f"  WARNING: parameter keys mismatch for {validated.name!r} "
                f"(expected {expected_keys}, got {actual_keys}), skipping"
            )
            continue

        print("  ->", validated.model_dump())
        results.append(validated.model_dump())

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(results)} results to {args.output}")

    elapsed = time.monotonic() - start_time
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total elapsed: {elapsed:.2f} seconds ({elapsed / 60:.2f} minutes)")


if __name__ == "__main__":
    main()

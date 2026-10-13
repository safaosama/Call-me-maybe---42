from typing import Any
from src.constrained import (
    allowed_for_options,
    select_best,
    allowed_for_literal,
)
from src.models import FunctionDefinition
from src.vocab import Vocab
import json
import re

NUMBER_PREFIX = re.compile(r"^-?\d*(\.\d*)?([eE]-?\d*)?$")
NOMATCH_PENALTY = 4.0


def _generate_literal(
    model: Any, vocab: Vocab, input_ids: list[int], target: str
) -> list[int]:
    """Generate an exact text value token by token."""
    produced = ""
    while produced != target:
        remaining = target[len(produced):]
        allowed = allowed_for_literal(vocab, remaining)
        next_id = max(allowed, key=lambda t: len(vocab.id_to_text[t]))
        input_ids = input_ids + [next_id]
        produced += vocab.id_to_text[next_id]
    return input_ids


def _generate_number(
    model: Any, vocab: Vocab, input_ids: list[int]
) -> list[int]:
    """Generate a number value one token at a time."""
    text = ""
    while True:
        logits = model.get_logits_from_input_ids(input_ids)
        allowed = [
            tid for tid, t in vocab.id_to_text.items()
            if t and NUMBER_PREFIX.match(text + t)
        ]
        best = logits.index(max(logits))
        if text and best not in allowed:
            break
        next_id = select_best(logits, allowed)
        text += vocab.id_to_text[next_id]
        input_ids = input_ids + [next_id]
    return input_ids


def _split_at_quote(s: str) -> tuple[str, bool]:
    """Find the first unescaped quote in a string."""
    i = 0
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == '"':
            return s[:i], True
        i += 1
    return s, False


def _generate_string_value(
    model: Any, vocab: Vocab, input_ids: list[int], max_tokens: int = 80
) -> tuple[list[int], str]:
    """Generate a string value without its quotes."""
    text = ""
    for _ in range(max_tokens):
        logits = model.get_logits_from_input_ids(input_ids)
        best = logits.index(max(logits))
        tok = vocab.id_to_text.get(best, "")
        if not text:
            tok = tok.lstrip()
        head, closed = _split_at_quote(text + tok)
        text = head
        if closed:
            break
        input_ids = input_ids + [best]
    try:
        text = json.loads('"' + text + '"')
    except json.JSONDecodeError:
        pass
    return input_ids, text


def vocab_decode(vocab: Vocab, ids: list[int]) -> str:
    """Convert token IDs into decoded text."""
    return "".join(vocab.id_to_text[i] for i in ids)


def model_instructions(functions: list[FunctionDefinition]) -> str:
    """Build instructions that describe the available functions."""
    lines = []
    for f in functions:
        params = ", ".join(f"{n}: {p.type}" for n, p in f.parameters.items())
        lines.append(f"- {f.name}({params}): {f.description}")
    lines.append(
        "- fn_nomatched(): no function above can do what the user asks."
    )
    return (
        "You are a function-calling assistant. You never answer the "
        "user's question. You only choose a function and fill in its "
        "arguments.\n\n"
        "Rules:\n"
        "1. Choose exactly ONE function from the list.\n"
        "2. Choose the function whose description matches the action "
        "the user asks for.\n"
        "3. Use fn_nomatched ONLY if the request is unrelated to every "
        "function (a general question, chat, or meaningless text).\n"
        "4. Copy argument values exactly from the user's request. "
        "Never invent values.\n"
        "5. Output only JSON: "
        '{"name": "<function>", "parameters": {...}}\n\n'
        "Available functions:\n" + "\n".join(lines)
    )


def _pick_function_name(
    model: Any,
    vocab: Vocab,
    input_ids: list[int],
    functions: list[FunctionDefinition],
) -> tuple[str, list[int]]:
    """Let the model choose one function name."""
    candidates = [f.name for f in functions] + ["fn_nomatched"]
    produced = ""
    ids = input_ids

    while len(candidates) > 1 and produced not in candidates:
        remaining_options = [
            c[len(produced):] for c in candidates
            if c.startswith(produced)
        ]
        real_options = [
            c[len(produced):] for c in candidates
            if c.startswith(produced) and c != "fn_nomatched"
        ]
        logits = model.get_logits_from_input_ids(ids)
        allowed = list(allowed_for_options(vocab, remaining_options))
        real_ids = allowed_for_options(vocab, real_options)

        def score(tid: int) -> float:
            penalty = 0.0 if tid in real_ids else NOMATCH_PENALTY
            return float(logits[tid] - penalty)
        next_id = max(allowed, key=score)
        ids = ids + [next_id]
        produced += vocab.id_to_text[next_id]

        candidates = [c for c in candidates if c.startswith(produced)]

    target = candidates[0]
    while produced != target:
        remaining = target[len(produced):]
        allowed = allowed_for_literal(vocab, remaining)
        next_id = max(allowed, key=lambda t: len(vocab.id_to_text[t]))
        ids = ids + [next_id]
        produced += vocab.id_to_text[next_id]

    return target, ids


def generate_function_call(
    model: Any,
    vocab: Vocab,
    prompt: str,
    functions: list[FunctionDefinition],
) -> dict[str, Any]:
    """Generate a function call from a user prompt."""
    if not prompt.strip():
        return {"prompt": prompt, "name": "fn_nomatched", "parameters": {}}
    header = (
        f"System: {model_instructions(functions)}\n"
        f"User: {prompt}\nAssistant: "
    )
    input_ids = model.encode(header)[0].tolist()

    input_ids = _generate_literal(
        model, vocab, input_ids, '{"name": "'
    )

    best_name, input_ids = _pick_function_name(
        model, vocab, input_ids, functions
    )
    if best_name == "fn_nomatched":
        return {
            "prompt": prompt,
            "name": "fn_nomatched",
            "parameters": {},
        }

    func = next(f for f in functions if f.name == best_name)

    input_ids = _generate_literal(
        model, vocab, input_ids, '", "parameters": {'
    )

    parameters: dict[str, Any] = {}
    param_items = list(func.parameters.items())
    for i, (param_name, spec) in enumerate(param_items):
        input_ids = _generate_literal(
            model, vocab, input_ids, f'"{param_name}": '
        )
        if spec.type in ("number", "integer"):
            before = len(input_ids)
            input_ids = _generate_number(model, vocab, input_ids)
            text = vocab_decode(vocab, input_ids[before:])
            try:
                n = float(text)
            except ValueError:
                n = 0.0
            parameters[param_name] = int(n) if spec.type == "integer" else n
        elif spec.type == "string":
            input_ids = _generate_literal(
                model, vocab, input_ids, '"'
            )
            input_ids, value = _generate_string_value(model, vocab, input_ids)
            parameters[param_name] = value
            input_ids = _generate_literal(
                model, vocab, input_ids, '"'
            )

        separator = ", " if i < len(param_items) - 1 else "}"
        input_ids = _generate_literal(
            model, vocab, input_ids, separator
        )

    input_ids = _generate_literal(model, vocab, input_ids, "}")

    return {"prompt": prompt, "name": best_name, "parameters": parameters}

from src.vocab import Vocab

NUMBER_CHARS = set("0123456789.-eE")


def allowed_for_literal(vocab: Vocab, remaining_target: str) -> list[int]:
    """Return token IDs that match the remaining target text."""
    return [
        tid
        for tid, text in vocab.id_to_text.items()
        if text and remaining_target.startswith(text)
    ]


def select_best(logits: list[float], allowed_ids: list[int]) -> int:
    """Select the highest-scoring allowed token ID."""
    if not allowed_ids:
        raise ValueError("No allowed tokens — the grammar/schema has a bug.")
    return max(allowed_ids, key=lambda tid: logits[tid])


def allowed_for_options(vocab: Vocab, options: list[str]) -> set[int]:
    """Return token IDs that start at least one of the options."""
    ids: set[int] = set()
    for opt in options:
        ids.update(allowed_for_literal(vocab, opt))
    return ids

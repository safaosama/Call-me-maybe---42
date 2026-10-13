import json
from pathlib import Path


def _byte_to_unicode_map() -> dict[str, int]:
    """Create a map from Unicode characters to byte values."""
    bs = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("\xa1"), ord("\xac") + 1))
        + list(range(ord("\xae"), ord("\xff") + 1))
    )
    cs = bs.copy()
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    unicode_chars = [chr(c) for c in cs]
    return {u: b for b, u in zip(bs, unicode_chars)}


_UNICODE_TO_BYTE = _byte_to_unicode_map()


def token_to_text(token: str) -> str:
    """Convert one vocabulary token into UTF-8 text."""
    raw_bytes = bytes(_UNICODE_TO_BYTE[ch] for ch in token)
    return raw_bytes.decode("utf-8", errors="replace")


class Vocab:
    """Store the mapping between token IDs and decoded text."""

    def __init__(self, vocab_file: str | Path):
        """Load the vocabulary file and create the token mapping."""
        with open(vocab_file, "r", encoding="utf-8") as f:
            raw_vocab: dict[str, int] = json.load(f)

        self.id_to_text: dict[int, str] = {
            token_id: token_to_text(raw_token)
            for raw_token, token_id in raw_vocab.items()
        }
        self.size = len(self.id_to_text)

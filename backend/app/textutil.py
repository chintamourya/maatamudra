import re
import unicodedata

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def norm_digits(s: str) -> str:
    """Map any Unicode decimal digit (Telugu, Devanagari, ...) to ASCII so numbers can be compared."""
    return "".join(str(unicodedata.decimal(ch)) if ch.isdecimal() else ch for ch in s)


def numbers(s: str, min_len: int = 1) -> set[str]:
    out = set()
    for m in _NUM.findall(norm_digits(s)):
        n = m.replace(",", "").rstrip(".")
        if len(n) >= min_len:
            out.add(n)
    return out

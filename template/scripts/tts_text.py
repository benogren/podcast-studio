"""Pre-TTS text normalization shared by the local render scripts.

Kokoro and Orpheus read bare 4-digit years as cardinal numbers
("1995" -> "one thousand nine hundred ninety-five"), so dialogue text is
normalized to spoken year forms before synthesis. Payload files on disk are
never modified -- normalization happens in memory at render time.
"""

import re

_ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]


def _two_digit(n):
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + ("-" + _ONES[ones] if ones else "")


def _year_words(year):
    hi, lo = divmod(year, 100)
    if hi == 20:
        if year == 2000:
            return "two thousand"
        if lo < 10:
            return "two thousand " + _ONES[lo]
        return "twenty " + _two_digit(lo)
    if lo == 0:
        return _two_digit(hi) + " hundred"
    if lo < 10:
        return _two_digit(hi) + " oh " + _ONES[lo]
    return _two_digit(hi) + " " + _two_digit(lo)


# Bare 1100-2099 tokens, not part of a larger number, identifier, or money
# figure ("$1995", "42,026", "v2026" are all left alone).
_YEAR = r"(1[1-9]\d{2}|20\d{2})"
_GUARD = r"(?<![A-Za-z0-9$,.])"
_RANGE_RE = re.compile(_GUARD + _YEAR + r"\s*[-–—]\s*" + _YEAR + r"\b(?!\d)")
_DECADE_RE = re.compile(_GUARD + _YEAR + r"s\b")
_SINGLE_RE = re.compile(_GUARD + _YEAR + r"\b(?!\d)")


def _decade_words(year):
    # Decades always end in -ty ("nineteen ninety") or "thousand".
    words = _year_words(year)
    if words.endswith("ty"):
        return words[:-2] + "ties"
    return words + "s"


def normalize_years(text):
    """Rewrite 4-digit years (1100-2099) into their spoken form."""
    text = _RANGE_RE.sub(
        lambda m: f"{_year_words(int(m.group(1)))} to {_year_words(int(m.group(2)))}",
        text,
    )
    text = _DECADE_RE.sub(lambda m: _decade_words(int(m.group(1))), text)
    text = _SINGLE_RE.sub(lambda m: _year_words(int(m.group(1))), text)
    return text

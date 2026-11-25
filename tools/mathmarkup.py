"""Convert inline `$...$` maths to `$$...$$` for the course site.

kramdown (Jekyll's Markdown engine) only treats `$$...$$` as maths; a single `$...$` reaches the
reader as literal dollar signs and can have its underscores eaten as emphasis. Notebooks keep
`$...$` (Jupyter and Colab render it); site pages and the handbook use `$$...$$`.
"""
from __future__ import annotations

import re

FENCE = re.compile(r"^(```|~~~).*?^\1", re.M | re.S)
CODE = re.compile(r"`[^`\n]+`")
INLINE = re.compile(r"(?<![\$\\\w])\$(?=[^\s$])([^$\n]+?)(?<=[^\s$\\])\$(?![\$\w])")


def to_double_dollar(md: str) -> str:
    keep: dict[str, str] = {}

    def stash(m: re.Match) -> str:
        key = f"\x00{len(keep)}\x00"
        keep[key] = m.group(0)
        return key

    md = FENCE.sub(stash, md)
    md = CODE.sub(stash, md)
    md = re.sub(r"\$\$.+?\$\$", stash, md, flags=re.S)  # leave existing $$...$$ alone
    md = INLINE.sub(r"$$\1$$", md)
    for key, value in reversed(list(keep.items())):
        md = md.replace(key, value)
    return md


def single_dollar_maths(md: str) -> list[str]:
    """Inline `$...$` spans left in a page (outside code); used by tests."""
    md = FENCE.sub("", md)
    md = CODE.sub("", md)
    md = re.sub(r"\$\$.+?\$\$", "", md, flags=re.S)
    return INLINE.findall(md)

"""Markdown helpers."""


def table(header: list, rows: list) -> str:
    """A Markdown table; short rows are padded. Cells must already be escaped."""
    width = max([len(header)] + [len(r) for r in rows])
    pad = lambda r: list(r) + [""] * (width - len(r))
    lines = ["| " + " | ".join(pad(r)) + " |" for r in [header, *rows]]
    return "\n".join([lines[0], "|" + "---|" * width] + lines[1:])

"""Convert the app's HTML cards to native Bot API rich documents.

The original HTML stays valid as a fallback. Only branded cards are eligible;
arbitrary broadcasts, logs and explicit entity-based messages are untouched.
"""

from __future__ import annotations

import re


CARD_DIVIDER = re.compile(r"^[━─]{8,}$")
METRIC = re.compile(r"^[╭│╰]\s*(.*?)\s{2,}(<b>.+)$")


def is_card(text: str) -> bool:
    return any(CARD_DIVIDER.fullmatch(line.strip()) for line in text.splitlines()[:5])


def render_rich_html(text: str) -> str:
    """Headings, responsive metric tables and expandable details, without media IO."""
    def details(match: re.Match[str]) -> str:
        content = match[1]
        title = re.match(r"<b>([^<]+)</b>\s*", content)
        summary = title[1] if title else "Подробности"
        body = content[title.end():] if title else content
        return f"<details><summary>{summary}</summary><p>{body.replace(chr(10), '<br>')}</p></details>"

    text = re.sub(
        r"<blockquote expandable>(.*?)</blockquote>",
        details,
        text,
        flags=re.DOTALL,
    )
    protected: dict[str, str] = {}

    def protect(match: re.Match[str]) -> str:
        token = f"__sirius_block_{len(protected)}__"
        protected[token] = match[0]
        return f"\n{token}\n"

    text = re.sub(r"<(pre|blockquote|details)\b[^>]*>.*?</\1>", protect, text, flags=re.DOTALL)
    blocks: list[str] = []
    paragraph: list[str] = []
    metrics: list[tuple[str, str]] = []

    def flush() -> None:
        if metrics:
            blocks.append("<table>" + "".join(
                f"<tr><td>{label}</td><td>{value}</td></tr>" for label, value in metrics
            ) + "</table>")
            metrics.clear()
        if paragraph:
            blocks.append("<p>" + "<br>".join(paragraph) + "</p>")
            paragraph.clear()

    for line in text.splitlines():
        line = line.strip()
        if not line or CARD_DIVIDER.fullmatch(line):
            flush()
            continue
        metric = METRIC.match(line)
        if metric:
            if paragraph:
                flush()
            metrics.append((metric[1], metric[2]))
            continue
        if metrics:
            flush()
        if line in protected:
            flush()
            blocks.append(protected[line])
        elif not blocks and not paragraph and "<b>" in line:
            blocks.append(f"<h2>{line}</h2>")
        elif line.startswith("❖") and "<b>" in line:
            flush()
            blocks.append(f"<h3>{line.removeprefix('❖').strip()}</h3>")
        elif line.startswith("⟡"):
            flush()
            blocks.append(f"<footer>{line.removeprefix('⟡').strip()}</footer>")
        else:
            # Legacy frame decorations become ordinary readable text.
            paragraph.append(re.sub(r"^[╭│╰]\s*", "", line))
    flush()
    return "".join(blocks)

"""Convert a Markdown report to a styled, self-contained HTML document."""
from __future__ import annotations

import html as _html
import re
from pathlib import Path
from urllib.parse import urlsplit

_CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.55;
  max-width: 920px;
  margin: 2rem auto;
  padding: 0 1.5rem;
  color: #111;
  background: #fff;
}
@media (prefers-color-scheme: dark) {
  body { background: #0e0f12; color: #e6e6e6; }
  a { color: #7ab7ff; }
  th { background: #1a1d23; }
  code, pre { background: #1a1d23; }
  blockquote { border-left-color: #444; color: #cfcfcf; }
}
h1, h2, h3, h4 { line-height: 1.25; margin-top: 2rem; }
h1 { font-size: 1.9rem; border-bottom: 1px solid currentColor; padding-bottom: .3rem; }
h2 { font-size: 1.4rem; }
h3 { font-size: 1.15rem; }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: .92rem; }
th, td { border: 1px solid #ccc; padding: .45rem .55rem; vertical-align: top; text-align: left; }
th { background: #f3f4f6; }
tr:nth-child(even) td { background: rgba(127,127,127,.06); }
code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background: #f3f4f6; }
pre { padding: .8rem 1rem; overflow-x: auto; border-radius: 6px; }
code { padding: .1rem .35rem; border-radius: 4px; }
blockquote {
  border-left: 3px solid #bbb;
  padding: .25rem 1rem;
  color: #555;
  margin: 1rem 0;
  background: rgba(127,127,127,.05);
}
.footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #ccc; font-size: .85rem; color: #666; }
"""


def _escape(s: str) -> str:
    return _html.escape(s, quote=True)


def _render_inline(text: str) -> str:
    """Minimal inline Markdown: bold, italic, inline code, links."""
    # Escape first, then re-insert formatting.
    out = _escape(text)
    # Inline code
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    # Only allow ordinary web URLs. Never turn an untrusted source value into
    # a javascript:, data:, file:, or other executable/privileged link.
    def safe_link(match: re.Match[str]) -> str:
        href = _html.unescape(match.group(2))
        try:
            parsed = urlsplit(href)
        except ValueError:
            return match.group(1)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return match.group(1)
        safe_href = _html.escape(href, quote=True)
        return f'<a href="{safe_href}" rel="nofollow noopener">{match.group(1)}</a>'

    out = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", safe_link, out)
    # Bold **text**
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    # Italic *text* (single, not part of **)
    out = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", out)
    return out


def markdown_to_html(md: str, *, title: str = "Background Research Report") -> str:
    """Render a subset of Markdown sufficient for our report template to HTML."""
    lines = md.splitlines()
    out: list[str] = []
    in_table = False
    table_rows: list[list[str]] = []

    def flush_table() -> None:
        nonlocal in_table, table_rows
        if not table_rows:
            in_table = False
            return
        out.append("<table>")
        # First row is header, second is the separator (dashes), rest body.
        header = table_rows[0]
        body = table_rows[2:] if len(table_rows) > 2 else []
        out.append(
            "<thead><tr>"
            + "".join(f"<th>{_render_inline(c)}</th>" for c in header)
            + "</tr></thead>"
        )
        if body:
            out.append("<tbody>")
            for row in body:
                out.append(
                    "<tr>" + "".join(f"<td>{_render_inline(c)}</td>" for c in row) + "</tr>"
                )
            out.append("</tbody>")
        out.append("</table>")
        table_rows = []
        in_table = False

    in_blockquote = False

    def flush_blockquote() -> None:
        nonlocal in_blockquote
        if in_blockquote:
            out.append("</blockquote>")
            in_blockquote = False

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        # Table handling: lines starting with | and containing |
        if line.startswith("|") and "|" in line[1:]:
            flush_blockquote()
            in_table = True
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            table_rows.append(cells)
            i += 1
            continue
        if in_table and not line.startswith("|"):
            flush_table()

        # Blockquote
        if line.startswith("> "):
            if not in_blockquote:
                out.append("<blockquote>")
                in_blockquote = True
            out.append(_render_inline(line[2:]) + "<br>")
            i += 1
            continue
        flush_blockquote()

        # Headings
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{_render_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^-{3,}$", line.strip()):
            out.append("<hr>")
            i += 1
            continue

        # List items
        if re.match(r"^\s*[-*]\s+", line):
            out.append("<ul>")
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                item = re.sub(r"^\s*[-*]\s+", "", lines[i])
                out.append(f"<li>{_render_inline(item)}</li>")
                i += 1
            out.append("</ul>")
            continue

        # Blank line → paragraph break
        if not line.strip():
            out.append("")
            i += 1
            continue

        # Paragraph (consume consecutive non-blank non-special lines)
        para: list[str] = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith((
            "#", "> ", "|", "- ", "* ",
        )):
            para.append(lines[i].rstrip())
            i += 1
        if para:
            out.append("<p>" + "<br>".join(_render_inline(p) for p in para) + "</p>")

    flush_table()
    flush_blockquote()

    body_html = "\n".join(out)
    return (
        f"<!doctype html>\n<html lang=\"en\"><head>\n"
        f"<meta charset=\"utf-8\">\n"
        f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        f"<title>{_escape(title)}</title>\n"
        f"<style>{_CSS}</style>\n"
        f"</head><body>\n"
        f"{body_html}\n"
        f"<div class=\"footer\">Rendered by osint-interview-agent.</div>\n"
        f"</body></html>\n"
    )


def write_html(md: str, out_path: Path, *, title: str = "Background Research Report") -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown_to_html(md, title=title), encoding="utf-8")
    return out_path

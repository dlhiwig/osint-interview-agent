"""Markdown → HTML export tests."""
from __future__ import annotations

from osint_agent.html_export import markdown_to_html


def test_headings_and_paragraphs():
    md = "# Title\n\nA paragraph with **bold** and *italic* and `code`.\n"
    out = markdown_to_html(md)
    assert "<h1>Title</h1>" in out
    assert "<strong>bold</strong>" in out
    assert "<em>italic</em>" in out
    assert "<code>code</code>" in out


def test_table_renders_headers_and_rows():
    md = (
        "# T\n\n"
        "| a | b |\n"
        "|---|---|\n"
        "| 1 | 2 |\n"
        "| 3 | 4 |\n"
    )
    out = markdown_to_html(md)
    assert "<table>" in out
    assert "<th>a</th>" in out
    assert "<td>3</td>" in out


def test_blockquote_and_link():
    md = "> Quoted line\n\nSee [docs](https://example.com/doc).\n"
    out = markdown_to_html(md)
    assert "<blockquote>" in out
    assert "</blockquote>" in out
    assert '<a href="https://example.com/doc"' in out


def test_escapes_html_in_cell_content():
    md = "| col |\n|---|\n| <script>x</script> |\n"
    out = markdown_to_html(md)
    assert "<script>x</script>" not in out
    assert "&lt;script&gt;" in out


def test_horizontal_rule():
    md = "A\n\n---\n\nB\n"
    out = markdown_to_html(md)
    assert "<hr>" in out


def test_output_has_viewport_meta():
    out = markdown_to_html("# H", title="My Title")
    assert "<title>My Title</title>" in out
    assert 'name="viewport"' in out

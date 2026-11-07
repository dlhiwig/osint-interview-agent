"""Typer-based CLI."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .agent import OSINTAgent, ResearchRequest
from .config import load_settings
from .html_export import write_html
from .logging_config import configure_logging

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="OSINT interview-prep agent.",
)
console = Console()


@app.callback()
def _root(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only warnings and errors."),
) -> None:
    if verbose:
        configure_logging("DEBUG")
    elif quiet:
        configure_logging("WARNING")
    else:
        configure_logging()


@app.command()
def research(
    subject: str = typer.Argument(..., help="Full name of the subject."),
    role: str = typer.Option("", help="Role or title the subject is being interviewed for."),
    company: str = typer.Option("", help="Hiring company."),
    authorization: str = typer.Option(
        "",
        "--authorization",
        "-a",
        help="Operator authorization statement. Required unless --dry-run.",
    ),
    provider: str = typer.Option(
        "",
        help="Override OSINT_LLM_PROVIDER (openai|anthropic).",
    ),
    model: str = typer.Option("", help="Override OSINT_LLM_MODEL."),
    out: Path | None = typer.Option(
        None,
        help="Report output path. Default: reports/<slug>-<timestamp>.md",
    ),
    html: bool = typer.Option(
        False,
        "--html",
        help="Also write an HTML-rendered copy of the report next to the Markdown.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Do not call the LLM; list available tools."
    ),
) -> None:
    """Run the research agent on one subject."""
    settings = load_settings()
    if provider:
        settings.osint_llm_provider = provider  # type: ignore[assignment]
    if model:
        settings.osint_llm_model = model

    if dry_run:
        _dry_run(settings, subject)
        return

    if not authorization:
        console.print("[red]Error:[/red] --authorization is required unless --dry-run is set.")
        raise typer.Exit(2)

    context: dict[str, str] = {}
    if role:
        context["role"] = role
    if company:
        context["company"] = company

    try:
        agent = OSINTAgent(settings=settings)
    except RuntimeError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(2) from e

    result = agent.research(
        ResearchRequest(
            subject_name=subject,
            context=context,
            authorization=authorization,
        )
    )

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.report_markdown, encoding="utf-8")
        console.print(f"[green]Report written to[/green] {out}")
        md_path: Path = out
    else:
        md_path = result.report_path  # type: ignore[assignment]
        console.print(f"[green]Report:  [/green] {md_path}")

    if html and md_path:
        html_path = md_path.with_suffix(".html")
        write_html(result.report_markdown, html_path, title=f"Report — {subject}")
        console.print(f"[green]HTML:    [/green] {html_path}")

    console.print(f"[green]Evidence:[/green] {result.evidence_path}")
    console.print(f"Evidence records: {len(result.evidence_records)}")
    console.print(f"Audit entries:    {len(result.audit_entries)}")


@app.command("self-audit")
def self_audit(
    name: str = typer.Argument(..., help="Your own full name (public-facing)."),
    role: str = typer.Option("", help="Your role, for context."),
    out: Path | None = typer.Option(None, help="Report output path."),
    html: bool = typer.Option(False, "--html", help="Also write an HTML copy."),
    provider: str = typer.Option("", help="Override OSINT_LLM_PROVIDER."),
    model: str = typer.Option("", help="Override OSINT_LLM_MODEL."),
) -> None:
    """Research your own public digital footprint (safer default use case)."""
    settings = load_settings()
    if provider:
        settings.osint_llm_provider = provider  # type: ignore[assignment]
    if model:
        settings.osint_llm_model = model

    try:
        agent = OSINTAgent(settings=settings)
    except RuntimeError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(2) from e

    authorization = (
        f"Self-audit: operator is the subject ({name}) researching their own "
        "public digital footprint. Consent-based; no third-party involvement."
    )
    context: dict[str, str] = {}
    if role:
        context["role"] = role

    result = agent.research(
        ResearchRequest(subject_name=name, context=context, authorization=authorization)
    )

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.report_markdown, encoding="utf-8")
        md_path: Path = out
        console.print(f"[green]Self-audit report:[/green] {md_path}")
    else:
        md_path = result.report_path  # type: ignore[assignment]
        console.print(f"[green]Self-audit report:[/green] {md_path}")

    if html and md_path:
        html_path = md_path.with_suffix(".html")
        write_html(result.report_markdown, html_path, title=f"Self-audit — {name}")
        console.print(f"[green]HTML:             [/green] {html_path}")

    console.print(f"[green]Evidence:         [/green] {result.evidence_path}")


@app.command()
def verify(
    evidence_csv: Path = typer.Argument(..., exists=True, help="Path to an evidence CSV from an earlier run."),
    fail_threshold: int = typer.Option(
        0,
        help="Exit with code 1 if more than this many URLs are unreachable.",
    ),
) -> None:
    """Re-check every source URL in a prior evidence CSV (link-rot probe)."""
    from .verify import summarize, verify_csv  # local to keep CLI import light

    rows = verify_csv(evidence_csv)
    summary = summarize(rows)

    table = Table(title=f"Evidence verification — {evidence_csv.name}")
    table.add_column("#", justify="right")
    table.add_column("URL")
    table.add_column("Confidence")
    table.add_column("Status", justify="right")
    table.add_column("OK")
    for i, r in enumerate(rows, start=1):
        marker = "[green]✓[/green]" if r.ok else "[red]✗[/red]"
        table.add_row(str(i), r.url, r.confidence, str(r.status), marker)
    console.print(table)
    console.print(
        f"[bold]Total:[/bold] {summary['total']}  "
        f"[green]Reachable:[/green] {summary['reachable']}  "
        f"[red]Unreachable:[/red] {summary['unreachable']}"
    )
    if summary["unreachable"] > fail_threshold:
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Print package version."""
    from . import __version__

    console.print(__version__)


def _dry_run(settings, subject: str) -> None:
    table = Table(title=f"Tool availability (subject: {subject})")
    table.add_column("Tool")
    table.add_column("Status")
    for name, enabled in settings.available_tools().items():
        table.add_row(name, "[green]enabled[/green]" if enabled else "[red]disabled[/red]")
    console.print(table)
    console.print(f"[cyan]LLM provider:[/cyan] {settings.osint_llm_provider}")
    console.print(f"[cyan]LLM model:   [/cyan] {settings.osint_llm_model}")
    console.print(f"[cyan]Max turns:   [/cyan] {settings.osint_max_tool_turns}")
    console.print(f"[cyan]Report dir:  [/cyan] {settings.osint_report_dir}")


if __name__ == "__main__":  # pragma: no cover
    app()

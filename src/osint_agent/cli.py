"""Typer-based CLI."""
from __future__ import annotations

import json as _json
from dataclasses import asdict
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .agent import OSINTAgent, ResearchRequest, ResearchResult
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
    provider: str = typer.Option("", help="Override OSINT_LLM_PROVIDER (openai|anthropic|ollama)."),
    model: str = typer.Option("", help="Override OSINT_LLM_MODEL."),
    out: Path | None = typer.Option(
        None, help="Report output path. Default: reports/<slug>-<timestamp>.md"
    ),
    html: bool = typer.Option(
        False, "--html", help="Also write an HTML-rendered copy next to the Markdown."
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Also write a sibling .json with structured result (report path, evidence, audit).",
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

    md_path = _write_outputs(result, out, html, json_out, title=f"Report — {subject}")

    console.print(f"[green]Report:  [/green] {md_path}")
    console.print(f"[green]Evidence:[/green] {result.evidence_path}")
    console.print(f"Evidence records: {len(result.evidence_records)}")
    console.print(f"Audit entries:    {len(result.audit_entries)}")


@app.command("self-audit")
def self_audit(
    name: str = typer.Argument(..., help="Your own full name (public-facing)."),
    role: str = typer.Option("", help="Your role, for context."),
    out: Path | None = typer.Option(None, help="Report output path."),
    html: bool = typer.Option(False, "--html", help="Also write an HTML copy."),
    json_out: bool = typer.Option(False, "--json", help="Also write a sibling .json."),
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

    md_path = _write_outputs(result, out, html, json_out, title=f"Self-audit — {name}")
    console.print(f"[green]Self-audit report:[/green] {md_path}")
    console.print(f"[green]Evidence:         [/green] {result.evidence_path}")


@app.command()
def verify(
    evidence_csv: Path = typer.Argument(
        ..., exists=True, help="Path to an evidence CSV from an earlier run."
    ),
    fail_threshold: int = typer.Option(
        0, help="Exit with code 1 if more than this many URLs are unreachable."
    ),
) -> None:
    """Re-check every source URL in a prior evidence CSV (link-rot probe)."""
    from .verify import summarize, verify_csv

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


def _write_outputs(
    result: ResearchResult,
    out: Path | None,
    html: bool,
    json_out: bool,
    *,
    title: str,
) -> Path:
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.report_markdown, encoding="utf-8")
        md_path = out
    else:
        md_path = result.report_path  # type: ignore[assignment]

    if html and md_path:
        html_path = md_path.with_suffix(".html")
        write_html(result.report_markdown, html_path, title=title)
        console.print(f"[green]HTML:    [/green] {html_path}")

    if json_out and md_path:
        json_path = md_path.with_suffix(".json")
        payload = {
            "report_path": str(md_path),
            "evidence_path": str(result.evidence_path) if result.evidence_path else None,
            "evidence_records": [asdict(r) for r in result.evidence_records],
            "audit_entries": result.audit_entries,
        }
        json_path.write_text(_json.dumps(payload, indent=2, default=str), encoding="utf-8")
        console.print(f"[green]JSON:    [/green] {json_path}")

    return md_path


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
    console.print(f"[cyan]Workers:     [/cyan] {settings.osint_tool_workers}")
    console.print(f"[cyan]Cache:       [/cyan] {'on' if settings.osint_enable_cache else 'off'}")
    console.print(f"[cyan]Report dir:  [/cyan] {settings.osint_report_dir}")


if __name__ == "__main__":  # pragma: no cover
    app()

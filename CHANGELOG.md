# Changelog

All notable changes to this project will be documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-11-07

### Added
- Shared HTTP helpers (`osint_agent._http`) with retry and exponential backoff on connection errors and transient HTTP statuses (408, 425, 429, 5xx).
- Structured logging (`osint_agent.logging_config`); CLI `--verbose` / `--quiet` flags.
- HTML export (`osint_agent.html_export`): minimal Markdown-to-HTML converter with a light/dark-aware stylesheet; `research --html` and `self-audit --html` emit a sibling `.html` file.
- `osint-agent verify <evidence.csv>` subcommand — HEAD-probes every source URL and prints a table + exit code.
- `osint-agent self-audit "<Your Name>"` subcommand — produces a background report on the operator themselves with a built-in consent-based authorization statement.
- Example scripts: `examples/basic_usage.py`, `examples/hermes_integration.py`.
- GitHub Actions CI matrix on Python 3.11 / 3.12 across Ubuntu and Windows.
- MIT License, this changelog.

### Changed
- All search / public-records / archive / fetch tool wrappers now go through the retrying HTTP helpers; they log at `INFO` what they are about to do.
- Report template escape fixes: eliminated Python deprecation warnings about `\|` escapes.

### Fixed
- Typer CLI now correctly exposes `research` as a named subcommand (previously, a single-command Typer app collapsed it away).

## [0.1.0] — 2026-11-07

### Added
- Initial implementation: provider-agnostic LLM (OpenAI, Anthropic); search backends for Perplexity, Tavily, Serper, Brave; public-record lookups for FEC, SEC EDGAR, OpenSanctions; Wayback snapshot; readable-text fetch; evidence ledger + CSV; Markdown report rendering; audit JSONL.

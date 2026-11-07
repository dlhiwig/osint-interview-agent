# Changelog

All notable changes to this project will be documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-11-07

### Added
- **Parallel tool execution.** When the LLM proposes multiple tool calls in one turn, they now run concurrently in a `ThreadPoolExecutor` (size controlled by `OSINT_TOOL_WORKERS`, default 4). Order of tool-result messages is preserved.
- **In-session tool-result cache.** Identical `(tool_name, args)` calls within one research session return the earlier result. Write-style tools (`record_evidence`) are never cached. Disable with `OSINT_ENABLE_CACHE=false`.
- **Ollama provider.** `OSINT_LLM_PROVIDER=ollama` uses the local Ollama OpenAI-compatible endpoint at `OSINT_OLLAMA_BASE_URL` (default `http://127.0.0.1:11434/v1`). Lets this agent run against a local Hermes-style model stack.
- **GitHub tools:** `github_user`, `github_user_repos`, `github_search_users` for the subject's public technical work. Honors `GITHUB_TOKEN` for higher rate limits.
- **OpenCorporates tool:** `opencorporates_officer_search` for publicly recorded officer / director roles across jurisdictions.
- **Scholar tools:** `orcid_search` and `crossref_works` for researcher identification and publication record.
- **`--json` CLI flag** on `research` and `self-audit`: emits a sibling `.json` file with report path, full evidence list, and audit entries — easy to consume by downstream automation.
- **Retry-After honoring.** When a 429 or 503 response carries a `Retry-After` header (seconds or HTTP-date), the retrier waits exactly that long instead of applying its default exponential backoff.
- **Repo hygiene:** Dependabot config (weekly pip + GitHub Actions), issue templates (bug + feature), pre-commit config (ruff, large-file guard, private-key detector).

### Changed
- `OSINTAgent` now accepts a `base_url` for the OpenAI client, used when routing to Ollama or any OpenAI-compatible endpoint.
- `Settings.available_tools()` reports the new GitHub / OpenCorporates / Scholar tools.

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

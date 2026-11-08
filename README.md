# osint-interview-agent

A Python agent that drafts a **public-source background research report** on a specific authorized subject prior to a job interview. It operationalizes an OSINT-librarian methodology against grounded search backends and free public-record APIs, and emits a Markdown report plus an append-only CSV evidence ledger that cites every claim.

- Standalone package, importable by other Python agents (including Hermes).
- Provider-agnostic LLM (OpenAI or Anthropic), selected by env var.
- Grounded web search via Perplexity Sonar, Tavily, Serper, and Brave.
- Public records via FEC (campaign finance), SEC EDGAR, and OpenSanctions.
- Wayback snapshots and readable-text extraction.
- Every factual claim is written to a ledger with source URL, access timestamp, identity-match rationale, and qualitative confidence.

---

## ⚠️ Not a consumer report

**Read this before using the agent for anything that could affect a consequential decision.**

This agent is designed for **informal, authorized public-source research**, not regulated background screening. Whether its output is a consumer report under the Fair Credit Reporting Act (FCRA) depends on how information is assembled, furnished, and used; a disclaimer does not determine legal status. **Do not use this tool to make employment, housing, credit, insurance, or similar eligibility decisions** without appropriate legal advice and a compliant process. The software does not implement FCRA notice, authorization, dispute, or adverse-action requirements.

Operator responsibilities:

1. **Lawful purpose.** Use only for lawful purposes — e.g., informal preparation for a conversation, self-audit of your own public footprint, or consent-based research where the subject has explicitly agreed. Do not use the agent to stalk, harass, dox, discriminate against, or surveil anyone.
2. **Anti-discrimination.** Do not research or record protected-class attributes (race, religion, national origin, sex, sexual orientation, gender identity, pregnancy, disability, genetic information, age, union membership, veteran status, etc.). The system prompt instructs the model to exclude these; the operator is responsible for not steering it toward them.
3. **Identity matching is not identity confirmation.** A name match is a *lead*, not a fact. Arrests are not convictions. Absence of a finding is not evidence of absence. Every ledger row carries an `identity_match_rationale` field — read it.
4. **Retention.** Delete the report and its evidence CSV when the authorized purpose is complete. Do not share beyond the authorized audience.
5. **Correction.** If you ever use the report in a consequential context, honor subject correction requests.

The operator is solely responsible for lawful use. The authors of this software make no warranties about the accuracy or completeness of any report.

---

## Install

```bash
cd osint-interview-agent
python -m venv .venv
.venv\Scripts\activate       # Windows PowerShell
pip install -e ".[dev]"
cp .env.example .env         # then fill in keys you have
```

At least one LLM key (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) is required. Search backends are independently optional — the agent registers only the tools whose keys are present. `SEC_EDGAR_USER_AGENT` must include a contact email per the SEC's fair-access policy.

## Usage

**CLI**

```bash
# See which tools are enabled, without calling the LLM:
osint-agent research "Jane Doe" --dry-run

# Produce a report:
osint-agent research "Jane Doe" \
    --role "Senior Product Manager" \
    --company "Acme Inc." \
    --authorization "Internal interview prep; subject has been informed public-source research will be performed." \
    --provider openai --model gpt-4o \
    --html

# Research your own public footprint (safer default use case):
osint-agent self-audit "Your Full Name" --html

# Re-check every source URL in a prior evidence CSV (link-rot probe):
osint-agent verify reports/jane-doe-20261107T120000Z-evidence.csv

# Print version:
osint-agent version
```

The report lands at `reports/<slug>-<timestamp>.md` with a sibling `-evidence.csv`. A `reports/audit.jsonl` records every tool call. Add `--html` to also emit a styled, self-contained HTML copy next to the Markdown. Add `--verbose` / `--quiet` at the root for log-level control.

**Python API** (so Hermes or any other agent can wrap it)

```python
from osint_agent import OSINTAgent, ResearchRequest

agent = OSINTAgent()  # reads .env
result = agent.research(ResearchRequest(
    subject_name="Jane Doe",
    context={"role": "Senior PM", "company": "Acme"},
    authorization="Internal interview prep; consent-based research.",
))
print(result.report_path)
print(result.evidence_path)
```

## Available tools

| Tool                    | Backend               | Needs                  |
|-------------------------|-----------------------|------------------------|
| `web_search_grounded`   | Perplexity Sonar      | `PERPLEXITY_API_KEY`   |
| `web_search`            | Tavily                | `TAVILY_API_KEY`       |
| `search_news`           | Tavily (news mode)    | `TAVILY_API_KEY`       |
| `google_search`         | Serper                | `SERPER_API_KEY`       |
| `brave_search`          | Brave Search API      | `BRAVE_SEARCH_API_KEY` |
| `search_fec`            | api.open.fec.gov      | `FEC_API_KEY`          |
| `search_sec_edgar`      | efts.sec.gov          | `SEC_EDGAR_USER_AGENT` |
| `screen_opensanctions`  | api.opensanctions.org | (free)                 |
| `wayback_snapshot`      | archive.org           | (free)                 |
| `fetch_page`            | httpx + trafilatura   | (none)                 |
| `record_evidence`       | internal ledger       | (built-in)             |

## Design

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the roadmap and current gaps.

Prompts live in `src/osint_agent/prompts/`:
- `system.md` — the active execution-oriented system prompt.
- `methodology.md` — the full OSINT research methodology (meta-prompt), kept verbatim as reference.
- `report_template.md` — the Jinja2 report shell.

## Explicitly out of scope

- No username-correlation tools (Sherlock / Maigret). High false-positive risk.
- No facial recognition, reverse-image, phone-number lookup, breach-data search.
- No native PDF export. Markdown, HTML, structured JSON, and evidence CSV are supported.
- No web UI. CLI + Python API only.
- No automated identity confirmation. Search matches remain unverified leads until independently corroborated.

## Tests

```bash
pytest
```

Tests mock all HTTP with `pytest-httpx` and the LLM with a stub client — no network and no API keys required.

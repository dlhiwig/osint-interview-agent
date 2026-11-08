# OSINT Research Platform Roadmap

## Decision

Extend this existing Python repository rather than create a competing project. The objective is a **lawful, authorized, privacy-conscious public-source research assistant** that produces evidence-based reports, not covert person-tracking or regulated background-screening decisions.

## Current baseline (reviewed 2026-11-08)

The v0.3.0 codebase provides:

- CLI and Python API, with OpenAI, Anthropic, and local Ollama providers.
- Configurable search providers, official/public records connectors, Wayback and page retrieval.
- GitHub public-work, OpenCorporates, ORCID and Crossref tools.
- Markdown, HTML, JSON and CSV exports; local evidence ledger and JSONL audit.
- Parallel tool execution, per-session caching, CI on Python 3.11/3.12.
- Prompts that distinguish leads from confirmed identity and exclude private/sensitive information.

**Not established:** independent accuracy benchmarks, safe handling of all adversarial webpages, production security posture, and full audit-chain integrity. Source availability is not proof of a claim's truth.

## Release gates

### Phase A: Secure baseline (P0)

- [x] Reject blank authorization at CLI and Python API research boundary.
- [x] Use accurate FCRA language: legal status depends on actual preparation and use.
- [x] Disallow non-HTTP(S) Markdown links in generated HTML.
- [ ] Add explicit permitted-purpose / data-retention fields to ResearchRequest.
- [ ] Review report template, logs and exports for accidental personal-data exposure.
- [ ] Add privacy-focused threat model and security review.
- [ ] Confirm CI test and lint success on Linux and Windows.

**Acceptance:** no external research starts with missing authorization; HTML exports do not create executable scheme links.

### Phase B: Evidence integrity (P1)

- [ ] Add immutable evidence IDs, source type, date published, time retrieved, original URL, archive location, SHA-256 of capture, and collector version.
- [ ] Validate source URLs; prevent local-file, loopback, metadata-service and intranet access from URL fetchers (SSRF protection).
- [ ] Separate source assertion, identity match, and analyst inference.
- [ ] Require independent corroboration for high-confidence identity claims, or an explicit reviewer exception.
- [ ] Keep an append-only tamper-evident audit chain with content checksums.
- [ ] Add contradictions, correction records, and review decisions.

**Acceptance:** each material claim maps to independently inspectable evidence and reviewer notes. Synthetic cases with shared names cannot merge identities automatically.

### Phase C: Storage and access (P1)

- [ ] Implement SQLite for MVP; PostgreSQL migration as warranted.
- [ ] Maintain per-case authorization, retention deadline, deletion and correction status.
- [ ] Encrypt sensitive case records at rest; use least-privilege roles.
- [ ] Keep research artifacts outside Git, and add CI checks for accidental sample PII/secrets.
- [ ] Separate test fixtures (fictional) from real case data.

**Acceptance:** no case content or credentials are committed; deletion and audit requirements are verified.

### Phase D: Source adapters (P2)

- [ ] Establish terms-of-use, authentication, provenance, rate limiting and jurisdiction checks for every adapter.
- [ ] Validate existing SEC EDGAR, FEC, OpenSanctions, OpenCorporates, GitHub, Crossref and ORCID integrations against their current documentation.
- [ ] Integrate ArchiveBox capture only for permitted public URLs.
- [ ] Evaluate Sherlock/Maigret only for authorized, consent-based public-username self-audits; never treat matches as identity confirmation.
- [ ] Prefer official records over scraped summaries.

**Acceptance:** offline integration tests and documented live smoke tests against permitted, non-personal test sources.

### Phase E: Reviewed reporting (P2)

- [ ] Introduce a reviewer approval step before publishing a report.
- [ ] Include evidence table, contradictions, unresolved leads, coverage limitations, scope and retention notes.
- [ ] Generate structured case export and a reproducible PDF from reviewed evidence.
- [ ] Keep LLM-generated claims separate from verified findings.

**Acceptance:** a report cannot claim a verified identity merely because names or usernames match.

## Privacy and appropriate use

- No breach databases, credential harvesting, private-account enumeration, private contact-finding, facial recognition, biometric identification, or covert tracking.
- No collection of home addresses, family information or sensitive traits.
- No bypass of access controls, CAPTCHAs, paywalls, rate limits or platform restrictions.
- No political persuasion profiling or inference of private political beliefs.
- This project does **not** provide FCRA compliance; consequential screening requires a separately appropriate legal and compliance process.
- Use fictional or explicitly consented subjects for tests. Do not store live profiles in this repository.

## Technical next steps

1. Run the GitHub Actions matrix and examine all failures.
2. Audit URL fetchers for SSRF, redirect handling and data leakage.
3. Add reviewer and immutable evidence records before additional discovery tools.
4. Select a self-audit test case with explicit authorization.
5. Reevaluate storage, deployment and legal requirements before commercial use.

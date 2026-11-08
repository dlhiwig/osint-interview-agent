# Private operator deployment: Toba workstation and mobile client

## Operating concept

- **Toba** runs local LLM (Ollama), Python research API, source/evidence database, and report renderer.
- **Phone** accesses a mobile-optimized interface over a private, authenticated encrypted link. A mobile UI and secure remote access are **future work**, not features of v0.3.0.
- Repository remains source code only. Never commit actual research records, subject identifiers, classified information, controlled unclassified information (CUI), government-only records, access tokens, or reports.
- **Current GitHub repository is public.** A change of visibility and access control must be verified separately before any sensitive development artifacts are added.
- An official Army/HRC workflow requires appropriate approval, authorized information systems, applicable cybersecurity/OPSEC review, and suitable handling of any government information. A personal laptop or phone is not an approved Army intelligence system merely because its operator is a military officer.
- Local Ollama inference does not imply local-only collection: search provider APIs and destination websites receive queries unless they are disabled. Document every outbound data flow.

## Recommended topology

```text
Mobile browser (future PWA)
   | private authenticated encrypted tunnel
   v
Toba: loopback-bound reverse proxy -> FastAPI (future) -> review / research orchestrator
                                                  |-> Ollama local model
                                                  |-> approved public-source connectors
                                                  |-> SQLite/SQLCipher or approved encrypted DB
                                                  |-> local evidence archive
```

A secure remote link must not expose unauthenticated service ports to the Internet. Do not make Ollama's default API publicly reachable. Prefer device-level authentication, MFA, short sessions, TLS, and network access control.

## Human analytic functions

1. Requirements and research plan with bounded permitted sources.
2. Source registry with original URL, institution, date, document identifier, and precise page/section locator.
3. Evidence capture with SHA-256, original bytes, immutable copy, analyst annotations and review status.
4. Identity matching that never auto-confirms on a name or username alone.
5. Analysis of competing hypotheses, timelines and source dependency; every relationship is linked to primary evidence.
6. Mobile analyst brief with source drilldown, collection gaps and corrections.
7. Case closeout, access auditing and retention.

## Limits

OSINT analytical methods may support CI threat-awareness research from appropriate public sources, but HUMINT recruitment, elicitation, surveillance, restricted-system access, protected-source collection, and operational targeting are outside this software. Classified and CUI content must never flow through personal devices, public GitHub, or unapproved cloud APIs.

## Implementation gates

P0: repository/data separation, CI, authorization, security review.
P1: local encrypted case store, evidence provenance, permissioned source adapters.
P2: source-only analyst brief (current in PR), citation/locator tests, identity review.
P3: authenticated mobile access and local-only default processing, subject to security testing.
P4: operational pilot with fictional/public test data, documented governance approvals where required.

# Source-first intelligence research briefs

## Scope

Use **source_brief** mode to produce a concise internal analyst artifact centered on publicly accessible, authorized evidence. It does not print a recurring legal disclaimer. Application authorization and handling rules remain in force.

## Local configuration

Set `OSINT_REPORT_MODE=source_brief` in the operator's local `.env`. The default remains `standard` to preserve existing output and tests.

Set `OSINT_LLM_PROVIDER=ollama` for a local model if you want to avoid sending the LLM prompt to a cloud model provider. Public internet queries still disclose query terms to the destination/search provider, and actual LLM quality depends on the selected local model.

## Brief structure

- Intelligence requirement / bounded question
- Findings and analysis
- Source register with original URL, exact document title and page/section or record identifier
- Publication and collection date, exact supporting extract
- Identity-resolution rationale, independent corroboration
- Contradictions, alternative explanations and intelligence gaps
- Review status and any captured archive URL / content SHA-256

New metadata columns are optional for compatibility with existing CSVs. Blank metadata represents missing evidence, never automatic verification. New records default to `unreviewed`; automated reports must not be described as human-approved.

## Further engineering required

- Verify raw-source fetch, document pagination, and citation anchor precision.
- Compute real hashes from preserved source bytes, do not accept model-generated values as authoritative.
- Add rigorous source independence scoring, analyst confirmation state transitions and safe output rendering.
- Develop a mobile client and secure private tunnel; neither currently exists.
- Ensure data is never stored in Git or unapproved cloud services.

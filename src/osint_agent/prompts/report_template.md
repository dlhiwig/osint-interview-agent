# Background Research Report — {{ request.subject_name }}

**Generated:** {{ now }}

---

## 1. Purpose and authorization

**Operator authorization statement:**

> {{ request.authorization or "(not supplied — report scope is informal and narrow)" }}

## 2. Scope and exclusions

- **In scope:** public professional history, publications and talks, public business registrations, publicly disclosed officer/director roles, FEC/SEC filings naming the subject, sanctions/PEP screening, Wayback snapshots of removed pages.
- **Out of scope (not researched, not recorded):** private contact details, protected-class attributes, breach data, authenticated/paywalled content, biometric identification, account enumeration, personal relationships and family.

## 3. Subject identifiers (minimal)

- **Name:** {{ request.subject_name }}
{% if request.context -%}
{% for k, v in request.context.items() -%}
- **{{ k | capitalize }}:** {{ v }}
{% endfor -%}
{% endif -%}
{% if request.additional_identifiers -%}
{% for k, v in request.additional_identifiers.items() -%}
- **{{ k | capitalize }}:** {{ v }}
{% endfor -%}
{% endif %}

## 4. Executive summary and findings

{{ final_narrative }}

## 5. Evidence and confidence table

{% if records %}
| # | Claim | Source | Type | Published | Accessed | Identity match | Corroboration | Caveats | Confidence |
|---|-------|--------|------|-----------|----------|----------------|----------------|---------|------------|
{% for r in records -%}
| {{ loop.index }} | {{ r.claim | replace("|", "\\|") | replace("\n", " ") }} | [link]({{ r.source_url }}) | {{ r.source_type }} | {{ r.pub_date }} | {{ r.accessed_at }} | {{ r.identity_match_rationale | replace("|", "\\|") | replace("\n", " ") }} | {{ r.corroboration | replace("|", "\\|") | replace("\n", " ") }} | {{ r.caveats | replace("|", "\\|") | replace("\n", " ") }} | {{ r.confidence }} |
{% endfor %}
{% else %}
_No evidence rows were recorded. The agent did not find reliably corroborated public-source information for the specified subject. Treat the absence of findings as inconclusive, not exculpatory._
{% endif %}

## 6. Source register

{% if records %}
{% for r in records -%}
- [{{ r.source_url }}]({{ r.source_url }}) — accessed {{ r.accessed_at }}{% if r.extract %}  
  *Extract:* {{ r.extract }}{% endif %}
{% endfor %}
{% else %}
_No sources._
{% endif %}

## 7. Identity-resolution limitations

See per-row `identity_match` rationales in §5. Rows with **Low** confidence or thin identity-match reasoning are investigative leads, not verified facts about the subject. Do not act on them without independent confirmation.

## 8. Privacy and retention

- Retain this report only as long as the authorized purpose requires.
- Do not share it beyond the authorized audience.
- If the subject requests correction of a factual inaccuracy, honor the request.
- Destroy or redact copies when the authorized purpose has concluded.

## 9. Overall limitations

- Public-source research cannot establish facts about non-public conduct.
- Online records can be outdated, mis-attributed, or fabricated.
- Automated searches may miss the correct subject when multiple people share a name.
- This report is **not a consumer report under the Fair Credit Reporting Act** and must not be used as the sole or primary basis for a hiring, housing, credit, or insurance decision.

---

_Produced by osint-interview-agent. Tool-call audit entries: {{ audit | length }}._

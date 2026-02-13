# Candidate Sync & Deduplication Flow

## Architecture Overview

```mermaid
flowchart TD
    subgraph Sources["Data Sources"]
        EW["Expandi Webhook / CSV Import"]
        TK["Textkernel Resume Parser (Colab)"]
    end

    subgraph SourceTables["Source Tables (raw data)"]
        EN["expandi_network\n(17,843 rows)"]
        TR["textkernel_resumes\n(1,234 rows)\n+ 10 child tables"]
    end

    subgraph RPCLayer["RPC Dedup Layer"]
        UEC["upsert_expandi_candidate(payload)\n- Upserts into expandi_network\n- Calls sync function"]
        SEC["sync_expandi_to_candidates(id)"]
        STC["sync_textkernel_to_candidates(id)"]
    end

    subgraph DedupLogic["Dedup Cascade"]
        direction TB
        D1["1. Already linked?\n(expandi_id / textkernel_id)"]
        D2["2. LinkedIn URL match"]
        D3["3. Email match\n(case-insensitive)"]
        D4["4. Name match\n(textkernel only)"]
        D5["No match = new insert"]
    end

    subgraph Target["Unified Table"]
        C["candidates\n(18,831 rows)\nsource: expandi | textkernel | both"]
    end

    EW --> UEC
    TK --> TR
    TR -->|"After 11-table insert"| STC
    UEC --> EN
    UEC --> SEC
    SEC --> DedupLogic
    STC --> DedupLogic
    D1 -->|"Yes: update fields"| C
    D1 -->|No| D2
    D2 -->|"Match: merge, source=both"| C
    D2 -->|No| D3
    D3 -->|"Match: merge, source=both"| C
    D3 -->|No| D4
    D4 -->|"Match: merge, source=both"| C
    D4 -->|No| D5
    D5 -->|"Insert new row"| C
```

## Dedup Cascade by Source

### Expandi Contacts

```
1. expandi_id    -- already linked? update fields only
2. linkedin_url  -- strongest external identifier
3. email         -- very stable, case-insensitive
   (name match excluded -- historical false positives)
```

### Textkernel Resumes

```
1. textkernel_id -- already linked? update fields only
2. email         -- from textkernel_emails table
3. first + last  -- fallback, both must be non-null
```

## Merge Strategy

When a match is found, fields merge using COALESCE (keep existing, fill blanks):

```
Expandi-owned fields:     linkedin_url, contact_status, conversation_status,
                          concat_tags, connected_at, invited_at

Textkernel-owned fields:  professional_summary, highest_degree, skills_summary,
                          management_score, months_work_experience, cv_file_name

Shared fields:            first_name, last_name, email, phone,
                          current_title, current_company, location
                          (first non-null value wins)
```

## How to Call

```sql
-- Expandi: full pipeline (upsert source + sync to candidates)
SELECT upsert_expandi_candidate('{"id": 12345, "first_name": "John", ...}'::jsonb);

-- Textkernel: after your Colab script inserts into textkernel_* tables
SELECT sync_textkernel_to_candidates('resume-uuid-here'::uuid);

-- Re-sync an existing expandi contact
SELECT sync_expandi_to_candidates(12345);
```

## Current Stats (2026-02-13)

| Source | Count |
|---|---|
| expandi only | 17,602 |
| textkernel only | 989 |
| both (merged) | 240 |
| **total candidates** | **18,831** |

## Known Limitation

One candidate can only link to one textkernel resume (`textkernel_id` is unique).
If the same person has two resume files, the first one gets linked.
The second resume still enriches/updates the candidate's fields,
but its `textkernel_id` is not stored on the candidate row.

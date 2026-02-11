# Deduplication Method for `expandi_network`

When importing contacts into `expandi_network`, deduplication is applied in the following order. A record is skipped if it matches an existing row on any of these checks.

## Check Order

### 1. `profile_link` (strongest)
Each LinkedIn user has a unique profile URL. This is the primary dedup key.

### 2. `object_urn`
LinkedIn's internal numeric ID for each user. Catches cases where the same person appears with different URL formats (e.g., encoded `ACoAA...` vs clean slug).

### 3. `email` (case-insensitive)
Catches cases where the same person appears with different LinkedIn URLs but the same email address.

### 4. `first_name` + `last_name` + `job_title` (weakest)
Composite key for fuzzy matching. This is the weakest check and may produce false positives at large companies with common names. Use with caution.

## Current Implementation

The import scripts (`import_searches_to_network.py`, `import_3rd_set_to_network.py`) currently implement checks **1** and **3** only. Check **2** (object_urn) and check **4** (name + job_title) are not yet implemented in the scripts.

## Validation Results (2026-02-11)

After importing 17,843 total rows:

| Check | Duplicates Found |
|---|---|
| profile_link | 0 |
| object_urn | 0 |
| email | 0 |
| first_name + last_name + job_title | 2 groups (4 rows) |

The two name+job_title matches are:
- **Hana Ahmed** - two different LinkedIn profiles and emails, likely two accounts or two different people
- **Felix Rudebusch** - one correct profile, one with a mismatched profile link (corrupt source data from `cwe.csv`)

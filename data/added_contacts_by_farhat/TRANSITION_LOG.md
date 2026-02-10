# Transition: sourcemade_contacts -> expandi_network

## Date: 2026-02-10

## What changed

Client requested a simpler approach: instead of a separate `expandi_sourcemade_contacts` table
with `sourcemade_` prefixed columns, contacts now live directly in `expandi_network` with a
`source_file` column to track which CSV they came from.

## Migrations applied

1. **create_sourcemade_contacts_table** - Created initial separate table (now obsolete)
2. **rename_sourcemade_contacts_table** - Renamed to `expandi_sourcemade_contacts` (now obsolete)
3. **add_source_file_to_expandi_network** - Added `source_file` column to `expandi_network`
4. **move_sourcemade_to_network_and_drop** - Moved all 3,261 records into `expandi_network` and dropped the separate table

## Import results

- 9 CSV files processed from `added_contacts_by_farhat/`
- 3,375 initially imported into separate table
- 3,261 moved into `expandi_network` (114 were already present by profile_link)
- All imported records have `source_file` set to the CSV filename (e.g. "BK_CM", "BA_ITC")

## Records per source file

| source_file | count |
|-------------|-------|
| BK_CM       | 2,666 |
| BK_NIA      | 241   |
| IA_F (1)    | 168   |
| 1           | 95    |
| BK_IAE      | 66    |
| IA_o (1)    | 15    |
| BA_ITC      | 6     |
| ITA_N       | 4     |

## How to query imported contacts

```sql
-- All imported contacts
SELECT * FROM expandi_network WHERE source_file IS NOT NULL;

-- Contacts from a specific CSV
SELECT * FROM expandi_network WHERE source_file = 'BK_CM';

-- Count by source
SELECT source_file, COUNT(*) FROM expandi_network WHERE source_file IS NOT NULL GROUP BY source_file;
```

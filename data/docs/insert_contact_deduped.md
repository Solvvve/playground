# `insert_contact_deduped` Supabase Function

PostgreSQL function that inserts a contact into `expandi_network` with 4-tier deduplication.

## Deduplication Order

Checks are applied in this order (stops at first match):

1. `profile_link` - exact match
2. `object_urn` - exact match
3. `email` - case-insensitive match
4. `first_name` + `last_name` + `job_title` - exact match on all three

If any check matches, the row is **skipped** (not inserted).

## Usage

```sql
SELECT insert_contact_deduped(
  p_id := 12345,
  p_first_name := 'John',
  p_last_name := 'Doe',
  p_profile_link := 'https://www.linkedin.com/in/johndoe/',
  p_email := 'john@example.com',
  p_job_title := 'Software Engineer',
  p_company_name := 'Acme Corp',
  p_object_urn := 98765,
  p_location := 'Berlin, DE',
  p_source_file := 'my_file',
  p_source := 'manual'
);
```

All parameters are optional (default `NULL`). Only pass what you have. The `created_at` field is auto-set to `NOW()`.

## Return Value

Returns a JSON object:

```json
// Inserted successfully
{"status": "inserted", "id": 12345}

// Skipped (duplicate found)
{"status": "skipped", "reason": "profile_link_match", "existing_id": 456}
{"status": "skipped", "reason": "object_urn_match", "existing_id": 456}
{"status": "skipped", "reason": "email_match", "existing_id": 456}
{"status": "skipped", "reason": "name_jobtitle_match", "existing_id": 456}
```

## All Parameters

| Parameter | Type |
|---|---|
| p_id | bigint |
| p_first_name | text |
| p_last_name | text |
| p_email | text |
| p_phone | text |
| p_address | text |
| p_profile_link | text |
| p_public_identifier | text |
| p_profile_link_public_identifier | text |
| p_image_link | text |
| p_object_urn | bigint |
| p_job_title | text |
| p_company_name | text |
| p_company_universal_name | text |
| p_company_website | text |
| p_employee_count_start | integer |
| p_employee_count_end | integer |
| p_industries | text |
| p_location | text |
| p_follower_count | integer |
| p_contact_status | text |
| p_conversation_status | text |
| p_thread | text |
| p_invited_at | timestamptz |
| p_connected_at | timestamptz |
| p_concat_tags | text |
| p_owned_by | text |
| p_source_file | text |
| p_source | text |

import csv
import os
from pathlib import Path
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

SCRIPT_DIR = Path(__file__).parent
CSV_DIR = SCRIPT_DIR

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def parse_int(value: str) -> int | None:
    if not value or value.strip() == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def fetch_all_rows(column: str) -> list:
    batch_size = 1000
    all_data = []
    offset = 0
    while True:
        result = (
            supabase.table("expandi_network")
            .select(column)
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        all_data.extend(result.data)
        if len(result.data) < batch_size:
            break
        offset += batch_size
    return all_data


def get_existing_profile_links() -> set:
    rows = fetch_all_rows("profile_link")
    return {row["profile_link"] for row in rows if row["profile_link"]}


def get_existing_emails() -> set:
    rows = fetch_all_rows("email")
    return {row["email"].lower() for row in rows if row["email"] and row["email"].strip()}


def import_csv_file(csv_path: Path, existing_links: set, existing_emails: set, stats: dict):
    filename = csv_path.name
    source_name = csv_path.stem

    print(f"Processing: {filename}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    inserted = 0
    skipped_by_link = 0
    skipped_by_email = 0
    skipped_no_link = 0

    for row in rows:
        profile_link = row.get("profile_link", "").strip()

        if not profile_link:
            skipped_no_link += 1
            continue

        if profile_link in existing_links:
            skipped_by_link += 1
            continue

        email = (row.get("email") or "").strip()
        if email and email.lower() in existing_emails:
            skipped_by_email += 1
            continue

        record = {
            "id": parse_int(row.get("id", "")),
            "first_name": row.get("first_name") or None,
            "last_name": row.get("last_name") or None,
            "profile_link": profile_link,
            "job_title": row.get("job_title") or None,
            "company_name": row.get("company_name") or None,
            "email": email or None,
            "phone": row.get("phone") or None,
            "address": row.get("address") or None,
            "image_link": row.get("image_link") or None,
            "object_urn": parse_int(row.get("object_urn", "")),
            "public_identifier": row.get("public_identifier") or None,
            "profile_link_public_identifier": row.get("profile_link_public_identifier") or None,
            "follower_count": parse_int(row.get("follower_count", "")),
            "contact_status": row.get("contact_status") or None,
            "conversation_status": row.get("conversation_status") or None,
            "company_universal_name": row.get("company_universal_name") or None,
            "company_website": row.get("company_website") or None,
            "employee_count_start": parse_int(row.get("employee_count_start", "")),
            "employee_count_end": parse_int(row.get("employee_count_end", "")),
            "industries": row.get("industries") or None,
            "location": row.get("location") or None,
            "thread": row.get("thread") or None,
            "connected_at": row.get("connected_at") or None,
            "concat_tags": row.get("concat_tags") or None,
            "owned_by": row.get("owned_by") or None,
            "source_file": source_name,
            "source": "sourcemade_3rd_set",
        }

        try:
            supabase.table("expandi_network").insert(record).execute()
            existing_links.add(profile_link)
            if email:
                existing_emails.add(email.lower())
            inserted += 1
        except Exception as e:
            if "duplicate key" in str(e).lower():
                skipped_by_link += 1
                existing_links.add(profile_link)
            else:
                print(f"  Error inserting {profile_link}: {e}")

    print(f"  Inserted: {inserted}, Skipped by profile_link: {skipped_by_link}, Skipped by email: {skipped_by_email}, No profile_link: {skipped_no_link}")

    stats["total_inserted"] += inserted
    stats["total_skipped_link"] += skipped_by_link
    stats["total_skipped_email"] += skipped_by_email
    stats["total_no_link"] += skipped_no_link
    stats["files_processed"] += 1


def main():
    csv_files = sorted([f for f in CSV_DIR.glob("*.csv")])

    if not csv_files:
        print(f"No CSV files found in {CSV_DIR}")
        return

    print(f"Found {len(csv_files)} CSV files to process")
    print(f"Source directory: {CSV_DIR}\n")

    print("Fetching existing profile links for deduplication...")
    all_links = get_existing_profile_links()
    print(f"  {len(all_links)} in expandi_network")

    print("Fetching existing emails for deduplication...")
    all_emails = get_existing_emails()
    print(f"  {len(all_emails)} in expandi_network\n")

    stats = {
        "total_inserted": 0,
        "total_skipped_link": 0,
        "total_skipped_email": 0,
        "total_no_link": 0,
        "files_processed": 0,
    }

    for csv_path in csv_files:
        import_csv_file(csv_path, all_links, all_emails, stats)

    print("\n" + "=" * 50)
    print("IMPORT COMPLETE")
    print("=" * 50)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Total contacts inserted: {stats['total_inserted']}")
    print(f"Skipped (profile_link match): {stats['total_skipped_link']}")
    print(f"Skipped (email match): {stats['total_skipped_email']}")
    print(f"Records without profile_link: {stats['total_no_link']}")


if __name__ == "__main__":
    main()

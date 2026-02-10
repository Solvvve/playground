import csv
import os
from pathlib import Path
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

SCRIPT_DIR = Path(__file__).parent
CSV_DIR = SCRIPT_DIR  # CSVs are in the same directory as this script

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def parse_int(value: str) -> int | None:
    if not value or value.strip() == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def get_existing_profile_links() -> set:
    result = supabase.table("expandi_network").select("profile_link").execute()
    return {row["profile_link"] for row in result.data if row["profile_link"]}


def import_csv_file(csv_path: Path, existing_links: set, stats: dict):
    filename = csv_path.name
    source_name = csv_path.stem

    print(f"Processing: {filename}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    inserted = 0
    skipped_duplicates = 0
    skipped_no_link = 0

    for row in rows:
        profile_link = row.get("profile_link", "").strip()

        if not profile_link:
            skipped_no_link += 1
            continue

        if profile_link in existing_links:
            skipped_duplicates += 1
            continue

        record = {
            "id": parse_int(row.get("id", "")),
            "first_name": row.get("first_name") or None,
            "last_name": row.get("last_name") or None,
            "profile_link": profile_link,
            "job_title": row.get("job_title") or None,
            "company_name": row.get("company_name") or None,
            "email": row.get("email") or None,
            "phone": row.get("phone") or None,
            "address": row.get("address") or None,
            "industries": row.get("industries") or None,
            "location": row.get("location") or None,
            "contact_status": row.get("contact_status") or None,
            "follower_count": parse_int(row.get("follower_count", "")),
            "source_file": source_name,
        }

        try:
            supabase.table("expandi_network").insert(record).execute()
            existing_links.add(profile_link)
            inserted += 1
        except Exception as e:
            if "duplicate key" in str(e).lower():
                skipped_duplicates += 1
                existing_links.add(profile_link)
            else:
                print(f"  Error inserting {profile_link}: {e}")

    print(f"  Inserted: {inserted}, Duplicates skipped: {skipped_duplicates}, No profile_link: {skipped_no_link}")

    stats["total_inserted"] += inserted
    stats["total_duplicates"] += skipped_duplicates
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
    existing_links = get_existing_profile_links()
    print(f"Found {len(existing_links)} existing contacts in expandi_network\n")

    stats = {
        "total_inserted": 0,
        "total_duplicates": 0,
        "total_no_link": 0,
        "files_processed": 0,
    }

    for csv_path in csv_files:
        import_csv_file(csv_path, existing_links, stats)

    print("\n" + "=" * 50)
    print("IMPORT COMPLETE")
    print("=" * 50)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Total contacts inserted: {stats['total_inserted']}")
    print(f"Duplicates skipped: {stats['total_duplicates']}")
    print(f"Records without profile_link: {stats['total_no_link']}")


if __name__ == "__main__":
    main()

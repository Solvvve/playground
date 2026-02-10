import csv
import json
import os
from pathlib import Path
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

SCRIPT_DIR = Path(__file__).parent
CSV_DIR = SCRIPT_DIR.parent / "data" / "searches_exported"
PROGRESS_FILE = SCRIPT_DIR / "import_progress.json"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_progress(progress: dict):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def parse_connected_at(value: str) -> str | None:
    if not value or value.strip() == "":
        return None
    return value


def parse_bigint(value: str) -> int | None:
    if not value or value.strip() == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def load_csv_to_supabase(csv_path: Path, progress: dict):
    filename = csv_path.name
    search_name = csv_path.stem
    
    start_row = progress.get(filename, 0)
    print(f"Processing: {filename} (search_name: {search_name}, starting from row {start_row})")
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if start_row >= len(rows):
        print(f"  Already completed ({len(rows)} rows)")
        return
    
    rows_to_process = rows[start_row:]
    inserted_count = 0
    
    for i, row in enumerate(rows_to_process):
        record = {
            "webhook_event": "manual_import",
            "search_name": search_name,
            "campaign_name": None,
            "expandi_contact_id": parse_bigint(row.get("id", "")),
            "first_name": row.get("first_name") or None,
            "last_name": row.get("last_name") or None,
            "profile_link": row.get("profile_link") or None,
            "job_title": row.get("job_title") or None,
            "company_name": row.get("company_name") or None,
            "email": row.get("email") or None,
            "phone": row.get("phone") or None,
            "address": row.get("address") or None,
            "object_urn": parse_bigint(row.get("object_urn", "")),
            "image_link": row.get("image_link") or None,
            "tags": row.get("concat_tags") or None,
            "contact_status": row.get("contact_status") or None,
            "conversation_status": row.get("conversation_status") or None,
            "connected_at": parse_connected_at(row.get("connected_at", "")),
        }
        
        try:
            supabase.table("expandi_campaign_events").insert(record).execute()
            inserted_count += 1
            progress[filename] = start_row + i + 1
            
            if inserted_count % 50 == 0:
                save_progress(progress)
                print(f"  Progress: {inserted_count} rows inserted (total: {progress[filename]}/{len(rows)})")
                
        except Exception as e:
            save_progress(progress)
            print(f"  Error at row {start_row + i}: {e}")
            raise
    
    save_progress(progress)
    print(f"  Completed: {inserted_count} new rows (total: {progress[filename]}/{len(rows)})")


def main():
    csv_files = sorted(CSV_DIR.glob("*.csv"))
    
    if not csv_files:
        print(f"No CSV files found in {CSV_DIR}")
        return
    
    progress = load_progress()
    print(f"Found {len(csv_files)} CSV files to process")
    print(f"Progress file: {PROGRESS_FILE}\n")
    
    for csv_path in csv_files:
        load_csv_to_supabase(csv_path, progress)
        print()
    
    print("Done!")


if __name__ == "__main__":
    main()

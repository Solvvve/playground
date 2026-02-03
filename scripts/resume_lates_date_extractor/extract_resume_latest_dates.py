"""
Extract the latest dates from each resume in the textkernel normalized tables.
Outputs TWO CSVs:
  1. resume_latest_dates_all.csv - Uses ALL dates (start + end + last_education_date)
  2. resume_latest_dates_start_only.csv - Uses only START dates
"""

import os
import csv
from datetime import date
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

PAGE_SIZE = 1000


def fetch_all_paginated(table_name, select_columns):
    all_rows = []
    offset = 0
    while True:
        response = supabase.table(table_name).select(select_columns).range(offset, offset + PAGE_SIZE - 1).execute()
        if not response.data:
            break
        all_rows.extend(response.data)
        if len(response.data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def get_all_resumes():
    rows = fetch_all_paginated("textkernel_resumes", "id, file_name")
    return {r["id"]: r["file_name"] for r in rows}


def get_resume_names():
    rows = fetch_all_paginated("textkernel_contact", "resume_id, formatted_name, given_name, family_name")
    names = {}
    for r in rows:
        name = r.get("formatted_name")
        if not name:
            given = r.get("given_name") or ""
            family = r.get("family_name") or ""
            name = f"{given} {family}".strip()
        names[r["resume_id"]] = name or "Unknown"
    return names


def get_education_dates_all():
    rows = fetch_all_paginated("textkernel_education", "resume_id, start_date, end_date, last_education_date")
    dates = {}
    for r in rows:
        resume_id = r["resume_id"]
        if resume_id not in dates:
            dates[resume_id] = []
        for field in ["start_date", "end_date", "last_education_date"]:
            if r.get(field):
                dates[resume_id].append(("education", field, r[field]))
    return dates


def get_education_dates_start_only():
    rows = fetch_all_paginated("textkernel_education", "resume_id, start_date")
    dates = {}
    for r in rows:
        resume_id = r["resume_id"]
        if resume_id not in dates:
            dates[resume_id] = []
        if r.get("start_date"):
            dates[resume_id].append(("education", "start_date", r["start_date"]))
    return dates


def get_position_dates_all():
    rows = fetch_all_paginated("textkernel_positions", "resume_id, start_date, end_date")
    dates = {}
    for r in rows:
        resume_id = r["resume_id"]
        if resume_id not in dates:
            dates[resume_id] = []
        for field in ["start_date", "end_date"]:
            if r.get(field):
                dates[resume_id].append(("position", field, r[field]))
    return dates


def get_position_dates_start_only():
    rows = fetch_all_paginated("textkernel_positions", "resume_id, start_date")
    dates = {}
    for r in rows:
        resume_id = r["resume_id"]
        if resume_id not in dates:
            dates[resume_id] = []
        if r.get("start_date"):
            dates[resume_id].append(("position", "start_date", r["start_date"]))
    return dates


def parse_date(date_str):
    if not date_str:
        return None
    try:
        if isinstance(date_str, date):
            return date_str
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def find_latest_date(all_dates):
    latest = None
    latest_source = None
    for source, field, date_str in all_dates:
        d = parse_date(date_str)
        if d and (latest is None or d > latest):
            latest = d
            latest_source = f"{source}.{field}"
    return latest, latest_source


def process_and_write_csv(resumes, names, education_dates, position_dates, output_file, label):
    print(f"\nProcessing {label}...")
    results = []
    for resume_id, file_name in resumes.items():
        all_dates = []
        all_dates.extend(education_dates.get(resume_id, []))
        all_dates.extend(position_dates.get(resume_id, []))
        
        latest_date, latest_source = find_latest_date(all_dates)
        
        results.append({
            "file_name": file_name,
            "person_name": names.get(resume_id, "Unknown"),
            "latest_date": latest_date.isoformat() if latest_date else None,
            "latest_date_source": latest_source,
            "total_dates_found": len(all_dates)
        })

    # Sort: newest first, None values at the end
    results.sort(key=lambda x: (x["latest_date"] is not None, x["latest_date"] or "1900-01-01"), reverse=True)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file_name", "person_name", "latest_date", "latest_date_source", "total_dates_found"])
        writer.writeheader()
        writer.writerows(results)

    with_dates = sum(1 for r in results if r["latest_date"])
    without_dates = len(results) - with_dates
    print(f"  Written {len(results)} rows to {output_file}")
    print(f"  Resumes with dates: {with_dates}, without: {without_dates}")
    
    print(f"  Top 5 most recent:")
    for r in results[:5]:
        if r["latest_date"]:
            print(f"    {r['latest_date']} | {r['person_name'][:25]:<25} | {r['file_name'][:35]}")


def main():
    print("Fetching resumes...")
    resumes = get_all_resumes()
    print(f"Found {len(resumes)} resumes")

    print("Fetching contact names...")
    names = get_resume_names()

    # Version 1: All dates (start + end + last_education_date)
    print("\nFetching ALL education dates...")
    edu_all = get_education_dates_all()
    print("Fetching ALL position dates...")
    pos_all = get_position_dates_all()
    process_and_write_csv(resumes, names, edu_all, pos_all, "resume_latest_dates_all.csv", "ALL dates (start+end)")

    # Version 2: Start dates only
    print("\nFetching START-ONLY education dates...")
    edu_start = get_education_dates_start_only()
    print("Fetching START-ONLY position dates...")
    pos_start = get_position_dates_start_only()
    process_and_write_csv(resumes, names, edu_start, pos_start, "resume_latest_dates_start_only.csv", "START dates only")

    print("\n=== Done! ===")


if __name__ == "__main__":
    main()

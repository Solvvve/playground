"""
Textkernel Resume Parser JSON Schema Validator

This script validates Textkernel/Sovren resume parser JSON output and extracts
schema information for analysis.

Usage:
    python validate_textkernel_schema.py <json_file>
    python validate_textkernel_schema.py --extract-schema <json_file>
"""

import json
import sys
from typing import Any, Dict, List, Optional


def get_type_name(value: Any) -> str:
    """Get the type name of a value for schema generation."""
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "integer"
    elif isinstance(value, float):
        return "number"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, dict):
        return "object"
    else:
        return type(value).__name__


def extract_schema(obj: Any, path: str = "") -> Dict[str, Any]:
    """
    Recursively extract schema from a JSON object.
    Returns a schema-like structure describing the object.
    """
    if obj is None:
        return {"type": "null"}
    
    elif isinstance(obj, bool):
        return {"type": "boolean"}
    
    elif isinstance(obj, int):
        return {"type": "integer"}
    
    elif isinstance(obj, float):
        return {"type": "number"}
    
    elif isinstance(obj, str):
        return {"type": "string"}
    
    elif isinstance(obj, list):
        if len(obj) == 0:
            return {"type": "array", "items": {}}
        else:
            # Sample first item for schema
            return {
                "type": "array",
                "items": extract_schema(obj[0], f"{path}[0]")
            }
    
    elif isinstance(obj, dict):
        properties = {}
        for key, value in obj.items():
            properties[key] = extract_schema(value, f"{path}.{key}")
        return {
            "type": "object",
            "properties": properties
        }
    
    return {"type": "unknown"}


def validate_required_fields(data: Dict) -> List[str]:
    """
    Validate that required Textkernel fields are present.
    Returns a list of missing fields.
    """
    required_paths = [
        ("Value", "Top-level Value object"),
        ("Value.ResumeData", "Resume data container"),
        ("Info", "API response info"),
        ("Info.Code", "Response status code"),
    ]
    
    missing = []
    
    for path, description in required_paths:
        parts = path.split(".")
        current = data
        found = True
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                found = False
                break
        
        if not found:
            missing.append(f"{path} ({description})")
    
    return missing


def get_nested_value(data: Dict, path: str) -> Optional[Any]:
    """Get a nested value from a dict using dot notation."""
    parts = path.split(".")
    current = data
    
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    
    return current


def summarize_resume(data: Dict) -> Dict[str, Any]:
    """Extract a summary of the parsed resume."""
    resume_data = get_nested_value(data, "Value.ResumeData") or {}
    
    summary = {
        "status": get_nested_value(data, "Info.Code"),
        "message": get_nested_value(data, "Info.Message"),
        "credits_used": get_nested_value(data, "Info.TransactionCost"),
    }
    
    # Contact info
    contact = resume_data.get("ContactInformation", {})
    summary["name"] = get_nested_value(contact, "CandidateName.FormattedName")
    summary["email"] = contact.get("EmailAddresses", [])
    summary["phone"] = [t.get("Normalized") for t in contact.get("Telephones", [])]
    
    # Education
    education = resume_data.get("Education", {})
    summary["highest_degree"] = get_nested_value(education, "HighestDegree.Name.Normalized")
    summary["education_count"] = len(education.get("EducationDetails", []))
    
    # Employment
    employment = resume_data.get("EmploymentHistory", {})
    summary["years_experience"] = get_nested_value(employment, "ExperienceSummary.MonthsOfWorkExperience")
    if summary["years_experience"]:
        summary["years_experience"] = round(summary["years_experience"] / 12, 1)
    summary["positions_count"] = len(employment.get("Positions", []))
    
    # Skills
    skills = resume_data.get("Skills", {})
    summary["raw_skills_count"] = len(skills.get("Raw", []))
    summary["normalized_skills_count"] = len(skills.get("Normalized", []))
    
    # Languages
    summary["languages"] = [
        lang.get("Language") 
        for lang in resume_data.get("LanguageCompetencies", [])
    ]
    
    # Certifications
    summary["certifications_count"] = len(resume_data.get("Certifications", []))
    
    return summary


def print_schema_tree(schema: Dict, indent: int = 0) -> None:
    """Print schema in a tree-like format."""
    prefix = "  " * indent
    
    if schema.get("type") == "object":
        for key, value in schema.get("properties", {}).items():
            type_str = value.get("type", "unknown")
            if type_str == "object":
                print(f"{prefix}{key}: {{")
                print_schema_tree(value, indent + 1)
                print(f"{prefix}}}")
            elif type_str == "array":
                items_type = value.get("items", {}).get("type", "unknown")
                if items_type == "object":
                    print(f"{prefix}{key}: [")
                    print_schema_tree(value.get("items", {}), indent + 1)
                    print(f"{prefix}]")
                else:
                    print(f"{prefix}{key}: [{items_type}]")
            else:
                print(f"{prefix}{key}: {type_str}")
    elif schema.get("type") == "array":
        items = schema.get("items", {})
        if items.get("type") == "object":
            print_schema_tree(items, indent)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    extract_mode = "--extract-schema" in sys.argv
    json_file = sys.argv[-1]
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {json_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        sys.exit(1)
    
    print("=" * 60)
    print("TEXTKERNEL RESUME PARSER VALIDATION")
    print("=" * 60)
    
    # Validate required fields
    missing = validate_required_fields(data)
    if missing:
        print("\n[WARNING] Missing required fields:")
        for field in missing:
            print(f"  - {field}")
    else:
        print("\n[OK] All required fields present")
    
    # Print summary
    print("\n" + "-" * 60)
    print("RESUME SUMMARY")
    print("-" * 60)
    
    summary = summarize_resume(data)
    for key, value in summary.items():
        if value is not None and value != [] and value != 0:
            print(f"  {key}: {value}")
    
    # Extract and print schema if requested
    if extract_mode:
        print("\n" + "-" * 60)
        print("SCHEMA STRUCTURE")
        print("-" * 60)
        
        schema = extract_schema(data)
        print_schema_tree(schema)
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

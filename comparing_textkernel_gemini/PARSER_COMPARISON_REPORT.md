# CV Parser Comparison: Textkernel vs Gemini

I tested 4 parsing configurations on 3 CVs (English and German)

## Detailed Comparison

### 1. Data Extraction Accuracy

| Field | Textkernel (LLM activated) | Textkernel No LLM | Gemini Flash | Gemini Flash Lite |
|-------|------------------|-------------------|--------------|-------------------|
| Name & Contact | Excellent | Excellent | Excellent | Excellent |
| Job Titles | Complete | Sometimes missing | Complete | Complete |
| Employment Dates | Excellent | Excellent | Good | Good |
| Education | Good (formal only) | Good (formal only) | Excellent (includes training) | Good |
| Languages | Yes (no proficiency) | Yes (no proficiency) | Yes + proficiency levels | Yes + proficiency |
| Projects vs Jobs | Correctly separated | Often confused | Correctly separated | Correctly separated |
| Certifications | Buried in experience | Buried in experience | Extracted separately | Sometimes missed |

### 2. Best for
| Parser | Best For | Limitations |
|--------|----------|-------------|
| **Textkernel (LLM activated)** | Enterprise ATS, skill matching, compliance | Complex output, higher cost |
| **Textkernel No LLM** | Cost-sensitive enterprise use | Less accurate job titles, noisy output |
| **Gemini 2.5 Flash** | Modern apps, lean integrations | No skill taxonomy, no profession codes |
| **Gemini Flash Lite** | Budget-friendly quick parsing | Slightly less complete than Flash |

---

## 3. Output Size Comparison

| Parser | Avg. File Size | Lines of JSON |
|--------|----------------|---------------|
| Textkernel (LLM activated) | ~80KB | ~2,500 |
| Textkernel No LLM | ~100KB | ~3,500 |
| Gemini Flash | ~18KB | ~400 |
| Gemini Flash Lite | ~15KB | ~350 |
---

## 5. Known Issues

### Textkernel
- **No language proficiency levels** - knows someone speaks German, but not if it's B1 or C2
- **Training courses often missed** - focuses on formal degrees
- **Certifications merged into work history** - not extracted as separate entities
- **Large output files** - requires more storage and processing

### Gemini
- **No skill taxonomy/IDs** - cannot easily search "find all candidates with Python" across database
- **No profession classification** - no ISCO/ONET codes for standardized matching
- **No skill duration tracking** - doesn't calculate years of experience per skill
- **No full-text preservation** - original CV text not included

## Test Data

This comparison was performed on:
- `timeless-resume-en.pdf` - English CV, Data Science/AI background
- `CV-Albin-Azemi.pdf` - German CV, Real Estate background
- `Abdolrahman-Nooreddini-Lebenslauf-2025-05.pdf` - German CV, Construction Engineering background

# Greybase Semantic Search

## Technical Guide v2

##### For: Abdel (and future team members)

##### Status: Production MVP

##### Next Phase: LinkedIn Contacts

##### Version 2 Updates:

- Similarity threshold adjusted to 0.75
- Incremental update logic added
- Error handling for OpenAI API
- Batch API option for backfills
- LinkedIn enrichment strategy for Phase 2

## Part 1: The Big Picture

## What Are We Building?

##### A search system that understands meaning, not just keywords.

##### Old way (keyword search):

- You search 'IT Audit'
- System finds CVs that contain the exact words 'IT Audit'
- Misses: 'Informatikpruefung', 'Internal Controls Testing', 'SOX Compliance'

##### New way (semantic search):

- You search 'IT Audit'
- System understands the meaning of 'IT Audit'
- Finds all related concepts, even in different languages

## Why Are We Doing This?

##### We're building an AI-powered recruitment agency. The core advantage:

- Speed: Agent creates longlist in seconds, not hours
- Quality: Finds candidates that keyword search misses
- Intelligence: Understands context (IT Audit at a bank is not the same as IT Audit at a hotel)

## The Key Questions We Asked Ourselves

#### Question 1: What should we embed?

| Option | Problem |
|--------|---------|
| Entire CV as one vector | "Python" gets diluted by unrelated content. Cannot tell what matched. |
| Each skill separately | "IFRS" alone has no context. Where did they use it? How long? |
| Each position separately | Better, but misses skills that are not in the description text. |
| Positions + their skills | Best of both worlds. Context-rich vectors. |

##### Our decision: Embed positions enriched with their related skills.

#### Question 2: How do we connect skills to positions?

##### Textkernel already did this work for us. The FoundIn field tells us which skill was used in which position:

```json
{
  "Name": "IFRS",
  "MonthsExperience": 86,
  "FoundIn": [
    { "Id": "POS-1", "SectionType": "WORK HISTORY" },
    { "Id": "POS-2", "SectionType": "WORK HISTORY" }
  ]
}
```

##### We use this connection to build richer embeddings.

#### Question 3: How many embeddings per CV?

| Approach | Embeddings/CV | API Cost | Quality |
|----------|---------------|----------|---------|
| Embed every skill separately | ~50 | High | Low (no context) |
| Embed every position + profile | ~6 | Low | High |

##### Our decision: ~6 embeddings per CV. Cheaper and better.

#### Question 4: What about LinkedIn contacts?

##### They come next. But they have less data:

| Source | Data Available | Embedding Strategy |
|--------|----------------|-------------------|
| Greybase (CVs) | Full: Skills, positions, descriptions | Rich embeddings |
| LinkedIn contacts | Sparse: Name, title, company | Simple embeddings + enrichment |

##### The same table structure works for both. We just store different chunk_type values.


## Part 2: State of the Art vs. Our Approach

### What Would Be 'Perfect'?

##### If we had unlimited time and money:

- Multiple embedding models - Compare OpenAI, Cohere, Voyage for best results
- Hybrid search - Combine vector search with keyword search (BM25)
- Reranking - Use a second model to reorder results
- Fine-tuned embeddings - Train on recruitment-specific data
- Knowledge graph - Connect skills, companies, industries in a graph database

##### Cost: Weeks of work. Thousands of dollars. Complex infrastructure.

### What We're Doing (Best Price/Effort/Performance)

| Choice | Why |
|--------|-----|
| OpenAI text-embedding-3-large | Best general-purpose model. 3072 dimensions. Multi-language. |
| Supabase pgvector | Already in our stack. Good enough for 100k+ vectors. |
| Simple cosine similarity | Works well. No complex ranking needed yet. |
| Positions with skills | Context-rich without over-engineering. |
| Threshold 0.75 | Start strict, loosen if needed. Precision over recall. |

##### Cost: One day of work. ~$5 for embeddings. Zero new infrastructure.

### Where We Could Optimize Later

| Optimization | When to Do It | Effort |
|--------------|---------------|--------|
| Add hybrid search (keyword + vector) | When users complain about exact matches | 2-3 days |
| Add reranking | When result order is not good enough | 1-2 days |
| Fine-tune embeddings | When we have feedback data | 1-2 weeks |
| Move to dedicated vector DB | When we hit 500k+ vectors | 3-5 days |

##### For now: None of these are needed. We ship the simple version first.


## Part 3: What To Build (Step by Step)

### Architecture Overview

```
+---------------------------------------------------------+
|              Your existing candidates table             |
+---------------------------------------------------------+
                            |
                            | 1:N relationship
                            v
+---------------------------------------------------------+
|                   candidate_chunks                      |
|                                                         |
|   - profile chunks (1 per candidate)                    |
|   - position chunks (3-7 per candidate)                 |
|   - later: linkedin_sparse chunks                       |
+---------------------------------------------------------+
```

### Step 1: Create the Database Table

##### Time: 30 minutes

```sql
-- Enable vector extension
create extension if not exists vector;

-- Create the chunks table
create table candidate_chunks (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null,
  chunk_type text not null,
  content_text text not null,
  metadata jsonb default '{}',
  embedding vector(3072),
  embedding_model text default 'text-embedding-3-large',
  created_at timestamptz default now()
);

-- Create indexes
create index on candidate_chunks
  using hnsw (embedding vector_cosine_ops);
create index on candidate_chunks (candidate_id);
create index on candidate_chunks (chunk_type);
```

##### Why HNSW index? It is an approximate nearest neighbor algorithm. Makes searches fast (milliseconds) even with millions of vectors.

### Step 2: Build the Profile Chunk (n8n)

##### Time: 2 hours

##### A profile chunk is a summary of the entire candidate. Used for quick 'does this person fit at all?' searches.

##### What goes into it:

```
{Current Title} | {Current Employer}

{Professional Summary from CV}

Core Skills: {Top 12 skills by experience}
Industries: {Top 3 industry categories}
Experience: {X} years
```

##### Example output:

```
Audit Consultant | Deloitte

Results-driven professional with a strong analytical
background from Big 4 audit and experience in operational
support...

Core Skills: Auditing Skills, Business Process Improvement,
IFRS, GAAP, SAP Applications, Internal Controls...

Industries: Insurance and Finance, ICT, Administration
Experience: 10 years
```

#### n8n Code for Profile Chunk:

```javascript
const cv = $json;

// Get top skills sorted by experience
const topSkills = (cv.Skills?.Normalized || [])
  .filter(s => s.MonthsExperience?.Value)
  .sort((a, b) => (b.MonthsExperience.Value || 0) - (a.MonthsExperience.Value || 0))
  .slice(0, 12)
  .map(s => s.Name);

// Get top industries
const industries = (cv.Skills?.RelatedProfessionClasses || [])
  .slice(0, 3)
  .map(c => c.Name);

// Get current position info
const currentPos = cv.EmploymentHistory?.Positions?.[0];
const currentTitle = currentPos?.JobTitle?.Normalized || 'Unknown';
const currentEmployer = currentPos?.Employer?.Name?.Normalized || 'Unknown';

// Calculate years of experience
const months = cv.EmploymentHistory?.ExperienceSummary
  ?.MonthsOfWorkExperience || 0;
const years = Math.round(months / 12);

// Build the profile text
const profileText = `${currentTitle} | ${currentEmployer}

${cv.ProfessionalSummary || ''}

Core Skills: ${topSkills.join(', ')}
Industries: ${industries.join(', ')}
Experience: ${years} years`;

return {
  candidate_id: $('get_candidate').item.json.id,
  chunk_type: 'profile',
  content_text: profileText.trim(),
  metadata: {
    current_title: currentTitle,
    current_employer: currentEmployer,
    years_experience: years,
    top_skills: topSkills
  }
};
```

### Step 3: Build the Position Chunks (n8n)

##### Time: 3 hours

##### One embedding per job the candidate has held. Includes the job description AND the skills they used in that role.

##### The magic: Using FoundIn to connect skills to positions

```javascript
const position = $json;
const allSkills = $('get_skills').item.json.Normalized || [];
const positionId = position.Id;

// Find skills that belong to THIS position
const relevantSkills = allSkills
  .filter(skill => {
    const foundIn = skill.FoundIn || [];
    return foundIn.some(loc => loc.Id === positionId);
  })
  .map(skill => skill.Name)
  .slice(0, 10);

// Format dates
const startDate = position.StartDate?.Date?.substring(0, 7) || '?';
const endDate = position.IsCurrent
  ? 'present'
  : (position.EndDate?.Date?.substring(0, 7) || '?');

// Build position text
const positionText = `${position.JobTitle?.Normalized} at ${position.Employer?.Name?.Normalized}
${startDate} - ${endDate}

${position.Description || ''}

Key Skills: ${relevantSkills.join(', ')}`;

return {
  candidate_id: $('get_candidate').item.json.id,
  chunk_type: 'position',
  content_text: positionText.trim(),
  metadata: {
    position_id: positionId,
    job_title: position.JobTitle?.Normalized,
    employer: position.Employer?.Name?.Normalized,
    skills: relevantSkills
  }
};
```

##### Example output:

```
Audit Consultant at Deloitte
2020-09 - present

Led statutory and group audits for Shared Services Centre
clients, ensuring compliance with IFRS and local GAAP.
Assessed design and operating effectiveness of internal
controls, identified deficiencies, and recommended process
improvements...

Key Skills: Auditing Skills, IFRS, GAAP, SAP Applications,
Internal Controls, CRM, Data Mining, Dashboards
```

##### Why this is powerful: When someone searches 'IT Auditor with SAP experience at Big4', this chunk will match strongly because 'Audit Consultant' is similar to 'IT Auditor', 'Deloitte' = Big4, and 'SAP' is explicitly in the skills.

### Step 4: Generate Embeddings (n8n)

##### Time: 1 hour to set up, 2 hours to run for all CVs

#### Option A: Standard API (for single CVs / real-time)

```javascript
// HTTP Request node in n8n
// Method: POST
// URL: https://api.openai.com/v1/embeddings

{
  "model": "text-embedding-3-large",
  "input": "{{ $json.content_text }}"
}

// Response: data[0].embedding = [0.123, -0.456, ...]
// (3072 numbers)
```

#### Option B: Batch API (for backfills - 50% cheaper)

```javascript
// For large backfills, use OpenAI Batch API
// 1. Create a .jsonl file with all requests
// 2. Upload to OpenAI
// 3. Wait up to 24h for results
// 4. Download and process

// Cost: $0.065 per 1M tokens (vs $0.13 standard)
// Use this for initial backfill of 1300 CVs
```

##### Cost calculation:

- 1300 CVs x ~6 chunks = ~8000 embeddings
- Standard API: ~$3-5
- Batch API: ~$1.50-2.50 (50% savings)

### Step 5: Error Handling (Required)

##### Time: 1 hour

> **NOTE:** OpenAI API can fail. Without retry logic, your workflow breaks on the first error.

##### n8n Implementation:

```javascript
// Add an Error Trigger node after HTTP Request

// Retry logic:
// - Max retries: 3
// - Wait between retries: exponential backoff
//   - Attempt 1: wait 1 second
//   - Attempt 2: wait 2 seconds
//   - Attempt 3: wait 4 seconds

// On final failure:
// - Log to error table (candidate_id, error_message, timestamp)
// - Continue with next chunk (don't stop entire batch)
// - Review errors manually after backfill
```

##### Error logging table:

```sql
create table embedding_errors (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid not null,
  chunk_type text,
  error_message text,
  created_at timestamptz default now()
);
```

### Step 6: Incremental Updates (Required)

##### Time: 2 hours

> **NOTE:** Without this, you cannot add new CVs or update existing ones after go-live.

##### When a new CV is added:

```javascript
// Trigger: New row in candidates table
// Action: Run embedding workflow for this candidate only

// n8n: Use Supabase Trigger node
// -> Filter: operation = INSERT
// -> Run profile + position chunk creation
```

##### When a CV is updated:

```sql
-- First: Delete old chunks for this candidate
DELETE FROM candidate_chunks
WHERE candidate_id = $1;

-- Then: Create new chunks (same workflow as initial import)
```

##### n8n Workflow Structure:

```
[Supabase Trigger: candidates table]
              |
              v
   [Check: INSERT or UPDATE?]
              |
      +-------+-------+
      v               v
   INSERT          UPDATE
      |               |
      |     [Delete old chunks]
      |               |
      +-------+-------+
              v
   [Create profile chunk]
              |
              v
   [Create position chunks]
              |
              v
   [Generate embeddings]
              |
              v
   [Insert into candidate_chunks]
```

### Step 7: Create the Search Function

##### Time: 1 hour

```sql
create or replace function search_candidates(
  query_embedding vector(3072),
  similarity_threshold float default 0.75,
  max_results int default 30
)
returns table (
  candidate_id uuid,
  chunk_type text,
  content_text text,
  metadata jsonb,
  similarity float
)
language sql
as $$
  select
    cc.candidate_id,
    cc.chunk_type,
    cc.content_text,
    cc.metadata,
    1 - (cc.embedding <=> query_embedding) as similarity
  from candidate_chunks cc
  where 1 - (cc.embedding <=> query_embedding) > similarity_threshold
  order by cc.embedding <=> query_embedding
  limit max_results;
$$;
```

> **NOTE:** Threshold is 0.75 (not 0.65). Start strict, loosen if you get too few results.

### Step 8: Test It

##### Time: 1 hour

##### Test these queries after backfill:

| Query | What Should Match |
|-------|-------------------|
| IT Auditor Big4 | Audit positions at Deloitte, PwC, KPMG, EY |
| SAP IFRS experience | People with both SAP and IFRS in their skills |
| ServiceNow Developer | ServiceNow in skills or descriptions |
| Compliance Manager Banking | Compliance roles at banks |
| Wirtschaftspruefer (German) | Should find Auditors (cross-language!) |


## Part 4: What Comes Next

### Phase 2: LinkedIn Contacts

##### Same table, different chunk type. But with enrichment for better results.

#### Basic Approach (Minimum)

```javascript
// For LinkedIn contacts (sparse data)
const linkedinText = `${name} | ${title} at ${company}`;

return {
  candidate_id: linkedinContactId,
  chunk_type: 'linkedin_sparse',
  content_text: linkedinText,
  metadata: {
    source: 'linkedin',
    linkedin_url: url,
    data_richness: 'sparse'
  }
};
```

#### Better Approach (Recommended): Company Enrichment

##### Short titles like 'Senior IT Auditor at KPMG' work, but enrichment makes them stronger:

```javascript
// Company enrichment lookup table
const companyEnrichment = {
  'KPMG': 'Big4, Wirtschaftspruefung, Professional Services',
  'Deloitte': 'Big4, Consulting, Audit, Advisory',
  'Deutsche Bank': 'Banking, Financial Services, DAX',
  'Allianz': 'Insurance, Financial Services, DAX',
  'BaFin': 'Regulator, Financial Services, Government',
  // ... add ~50 relevant companies
};

const enrichment = companyEnrichment[company] || '';

const linkedinText = enrichment
  ? `${name} | ${title} at ${company} (${enrichment})`
  : `${name} | ${title} at ${company}`;

// Example output:
// "Max Mueller | Senior IT Auditor at KPMG
// (Big4, Wirtschaftspruefung, Professional Services)"
```

##### Why this helps:

- Search 'Big4 Auditor' finds KPMG, Deloitte, PwC, EY contacts
- Search 'Financial Services' finds banking AND insurance contacts
- Embedding model gets more semantic context

#### Phase 2 Timeline

| Task | Time |
|------|------|
| Basic LinkedIn import (no enrichment) | 2 hours |
| Build company enrichment table | 2 hours |
| LinkedIn import with enrichment | 3 hours |
| Testing | 1 hour |
| **Total** | **~1 day** |

### Phase 3: Apollo Leads, Juicebox, etc.

##### All flow through the same pipeline:

- Get data
- Build text chunks (with enrichment where possible)
- Embed
- Store in candidate_chunks
- Search finds everything

##### Upgrade path: When you get a full profile (Juicebox PDF to Textkernel), delete the sparse chunk and create full profile + position chunks.


## Part 5: Summary

### What We Built

| Component | Purpose |
|-----------|---------|
| candidate_chunks table | Store all embeddings in one place |
| Profile chunks | Quick "does this person fit?" matching |
| Position chunks (with skills) | Precise "do they have this experience?" matching |
| Search function | Find similar candidates by meaning |
| Error handling | Graceful failure, no lost data |
| Incremental updates | Add/update CVs after go-live |

### Time and Cost

| Task | Time | Cost |
|------|------|------|
| Database schema | 30 min | $0 |
| n8n profile logic | 2 hours | $0 |
| n8n position logic | 3 hours | $0 |
| OpenAI integration | 1 hour | $0 |
| Error handling | 1 hour | $0 |
| Incremental updates | 2 hours | $0 |
| Backfill 1300 CVs (Batch API) | 2 hours | ~$2 |
| Testing | 1 hour | $0 |
| **Total** | **~12 hours** | **~$2-5** |

### Key Decisions

- Embed positions with their skills (not skills separately)
- Use Textkernel's FoundIn mapping (don't reinvent the wheel)
- One table for all chunk types (easy to extend later)
- Start with threshold 0.75 (precision over recall)
- Use Batch API for backfills (50% cost savings)
- Error handling + incremental updates (production-ready)

### Definition of Done

- All 1300 CVs have profile + position chunks
- Search 'IT Auditor Financial Services' returns relevant results
- Results show context (not just skill names)
- New CVs are automatically embedded (incremental updates work)
- Errors are logged, not lost
- Ready for LinkedIn contacts in Phase 2

##### Questions? Ask in Slack. Let's ship this.

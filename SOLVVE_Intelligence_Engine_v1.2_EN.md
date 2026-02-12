# SOLVVE Intelligence Engine – Project Description v1.2

**Date:** February 10, 2026
**Author:** Faro (CEO), with CTO advisory
**Audience:** Dev team (Abdeljalil), Claude Code, external specialists
**Status:** Implementation kickoff

### Changelog v1.2 (February 10)
- Replaced inline SQL schemas with reference to deployable `SOLVVE_schema_v1.sql`
- Added companion docs: `SOLVVE_Stage_Reference.md`, `SOLVVE_Data_Source_Mapping.md`
- Section 3.3: Dedup now via `upsert_candidate()` Stored Procedure (RPC), not n8n logic
- Phase 0: Added Task 0.1b – Create SQL Views for NocoDB (BEFORE connecting NocoDB)
- Flow 1.1: Attio native Automations (Send Webhook), not polling
- Resolved T3: Attio has native automations with webhook actions
- Section 5a: Day-Zero-Revenue play – CSV export + Claude batch, no NocoDB needed for Day 1
- Section 6: Added Referral Workflow (Priority 1b)
- Phase 2: Flow 2.6 (Campaign Stats Aggregation) → deferred, use tool dashboards
- Phase 3: Flow 3.5 (Stepstone Matching) → simplified to email notification
- CV Parsing decision: Textkernel stays (normalized skill IDs > LLM flexibility)

### Changelog v1.1 (February 9)
- Simplified `candidates` schema (non-essential fields → JSONB `metadata`)
- Added Section 5a: Manual Process Validation (Week 1, before automation)
- Added Section 5b: QA Process – Sourcer Quality Control
- Added Section 6.1: Outreach Timing Rules (candidate experience)
- Added Section 9a: Revenue KPIs & Business Metrics + Team Performance KPIs
- Added Section 9b: Client-Facing Reporting
- Added Section 10: Fallback Processes + n8n Error Workflow + `failed_jobs` retry queue
- Added Task 0.0: Vector dimension check as Phase 0 blocker
- Added Task 0.6b: Resend setup for transactional consent emails
- Resolved T5: Consent emails via Resend, not Smartlead
- Added reply handling warning: plaintext only, no HTML parsing
- Added recommendation: budget for expert sessions for Junior-Dev blockers

---

## 1. Executive Summary

SOLVVE is a data-driven executive search boutique for BaFin-regulated companies. Our core advantage: we treat recruiting as a Data & Information Game. Instead of burning expensive InMails, we build a proprietary intelligence database that improves with every search.

**The system consists of three pillars:**

1. **Sourcing Engine** – Find candidates via Greybase (proprietary CV database with vector search), LinkedIn connections, Expandi lists, and external search tools
2. **Outreach Engine** – Multi-channel contact prioritized by cost: Phone → Email → Connection Request → InMail (last resort)
3. **Learning Loop** – Every campaign, every reply, every touchpoint flows back into the database and improves future searches

**Architecture decision:** Supabase (PostgreSQL + pgVector) is the Single Source of Truth. NocoDB is the UI for all users. No separate ATS – everything lives in one database, separated by views and status fields.

**Why no SaaS ATS (e.g. Manatal):**

- NocoDB works directly on Supabase – no sync, no duplicates
- pgVector search accesses all data (Greybase, ATS, LinkedIn contacts)
- Unlimited users (relevant for Philippines sourcer, Egypt recruiter)
- Full data ownership – a real selling point with BaFin clients
- 60-85% cheaper than SaaS ATS

---

## 2. Architecture Overview

```
┌─────────────┐     Webhook      ┌──────────┐     CRUD      ┌──────────────┐
│   Attio     │ ──────────────── │   n8n    │ ────────────► │  Supabase    │
│  (CRM/BD)   │                  │(Orchestr.)│              │  (PostgreSQL │
└─────────────┘                  └──────────┘              │  + pgVector) │
                                      │                     └──────┬───────┘
┌─────────────┐     Webhooks     │                          │
│  Expandi    │ ─────────────────┘                     ┌────┴───────┐
│ (Outreach)  │                                        │   NocoDB   │
└─────────────┘                                        │  (UI/Views)│
                                                       └────────────┘
┌─────────────┐     n8n
│ Smartlead   │ ─────────────────┐
│  (Email)    │                  │
└─────────────┘                  │
                                 ▼
┌─────────────┐          ┌──────────┐
│  Textkernel │          │  Claude  │
│ (CV Parse)  │          │  API /   │
└─────────────┘          │ Langdock │
                         └──────────┘
┌─────────────┐
│  Apollo.io  │  → Contact data enrichment
└─────────────┘
┌─────────────┐
│   Apify     │  → LinkedIn profile enrichment
└─────────────┘
┌─────────────┐
│  Juicebox   │  → Candidate search (Export → Supabase)
└─────────────┘
┌─────────────┐
│  LinkedIn   │  → Candidate search (→ Expandi directly)
│  Recruiter  │
└─────────────┘
┌─────────────┐
│  Stepstone  │  → Application intake → Matching
│  Direct     │
└─────────────┘
┌─────────────┐
│  tl;dv      │  → Interview transcription → Profile enrichment
└─────────────┘
┌─────────────┐
│ theirstack  │  → Company intelligence (Phase 3)
└─────────────┘
```

### Data Flow Principle

Everything flows into Supabase. Nothing stays isolated in external tools. Every interaction with a candidate is documented in Supabase – automatically via webhooks, not manually.

---

## 3. Supabase Data Model

### 3.1 Existing Tables (already in place)

**`greybase_candidates`** – ~1,200 parsed CVs
- Contact data, LinkedIn URL, email and phone where available
- Textkernel-parsed fields (positions, skills, employers, time periods)

**`greybase_chunks`** – Vector embeddings
- One chunk per career station + skills
- Embeddings via GPT (text-embedding-3-large or ada-002)
- pgVector index for similarity search

**`linkedin_contacts`** – ~5,000 LinkedIn connections (Faro)
- Basic profile data from LinkedIn export
- NOT yet enriched via Apify (→ Phase 1 task)

### 3.2 New Tables (to be created)

**⚠️ DEPLOYABLE SCHEMA:** The complete SQL schema is in `SOLVVE_schema_v1.sql`. Run it in Supabase SQL Editor. It contains all tables, indexes, views, triggers, and the `upsert_candidate()` stored procedure.

**Stage definitions:** See `SOLVVE_Stage_Reference.md` for the complete breakdown of what has stages, what the values mean, and how Job Stages / Candidate-in-Job Stages / Candidate Overall Status relate to each other.

**Data source mapping:** See `SOLVVE_Data_Source_Mapping.md` for how data from each source (Greybase, LinkedIn, Expandi, Juicebox, Apollo, Stepstone, Referrals) maps to the `candidates` table.

**Tables overview:**

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `candidates` | Unified candidate record (ALL sources) | linkedin_url (dedup), email, phone, source, consent_status, overall_status, cv_parsed, metadata JSONB, embedding |
| `jobs` | Open positions / search assignments | attio_deal_id, client_name, job_title, stage, metadata JSONB, embedding |
| `candidate_jobs` | Pipeline: candidate × job (the KANBAN) | candidate_id, job_id, stage, review_status (QA gate) |
| `touchpoints` | Every interaction logged | candidate_id, channel, direction, status, summary (plaintext only!) |
| `companies` | Company watchlist (manual first) | name, type, bafin_regulated, metadata JSONB |
| `failed_jobs` | n8n error retry queue | workflow_name, input_payload, error_text, resolved |

**SQL Views for NocoDB** (also in the SQL file – MUST be created before connecting NocoDB):

| View | Purpose | Used by |
|------|---------|---------|
| `v_candidates` | Searchable candidate list (no vector blobs, JSONB fields extracted) | Everyone |
| `v_pipeline` | Kanban-ready: candidate × job with all context | Faro / Recruiter |
| `v_jobs` | Jobs with candidate counts per stage | Faro |
| `v_qa_review` | Sourcer quality control queue | Faro |
| `v_hot_candidates` | Interested / in-process candidates | Faro / Recruiter |
| `v_touchpoints_recent` | Last 30 days of interactions | Everyone |

**⚠️ NocoDB + JSONB/VECTOR Warning:** NocoDB cannot filter inside JSONB fields and displays VECTOR(3072) columns as unreadable blobs. The SQL Views extract the relevant JSONB keys and hide the embedding columns. **Connect NocoDB to the Views, not the raw tables.** This is 2 hours of work and saves the entire team weeks of frustration.

**Design decisions:**
- `candidates.metadata` JSONB instead of 25+ columns: Fields like `regulatory_experience[]`, `tech_skills[]`, `profile_summary` will be empty for most candidates initially. Extract into dedicated columns later when data at scale. GDPR fields, dedup keys, and status fields are NOT optional – those are core from Day 1.
- `jobs.metadata` JSONB for extracted requirements: `key_skills`, `regulatory_context`, `tech_stack`, `target_companies` go here. Avoids rigid array columns that NocoDB handles poorly.
- `touchpoints.summary` instead of `message_content`: Do NOT store full HTML email threads. Plaintext excerpt max 500 chars or just a flag + link to Smartlead conversation.
- `candidate_jobs.review_status`: QA gate for sourcer quality control. Only 'approved' candidates proceed to outreach.
- **CV Parsing stays with Textkernel** (not LLM). Textkernel produces normalized skill IDs – critical for consistent matching. LLMs are cheaper but produce inconsistent skill labels ("Python" vs "Python Programming" vs "Coding in Python"). The normalization is worth the per-parse cost.

### 3.3 Deduplication – Via Stored Procedure (NOT n8n logic)

**Problem:** The same person can exist simultaneously in Greybase, LinkedIn contacts, Expandi lists, and Apollo.

**Solution: `upsert_candidate()` Stored Procedure**

Instead of building dedup logic in n8n (multiple HTTP nodes, race conditions, error-prone), the entire dedup runs as a single Supabase RPC call:

```
n8n calls: supabase.rpc('upsert_candidate', { p_linkedin_url, p_email, p_first_name, ... })
```

**What the function does (single atomic operation):**
1. Try match by `linkedin_url` (primary dedup key)
2. If no match → try match by `email` (secondary key)
3. If match found → UPDATE (enrich empty fields only, never overwrite existing data, merge JSONB metadata)
4. If no match → INSERT new candidate record
5. If `p_job_id` provided → auto-create `candidate_jobs` record with `review_status='pending_review'`
6. Returns: `{id: UUID, action: 'inserted' | 'updated'}`

**Parameters:** `p_linkedin_url`, `p_email`, `p_phone`, `p_first_name`, `p_last_name`, `p_current_title`, `p_current_company`, `p_location`, `p_source`, `p_source_details` (JSONB), `p_cv_raw_text`, `p_metadata` (JSONB), `p_job_id` (optional), `p_consent_status`

**Why this is better than n8n dedup logic:**
- **Atomic:** No race conditions when two imports run simultaneously
- **Fast:** Single database call instead of SELECT → IF → UPDATE/INSERT chain
- **Reusable:** Every import source (Expandi, Juicebox, Apollo, CSV) calls the same function
- **Testable:** Run directly in SQL Editor to verify behavior

**⚠️ RULE: ALL imports MUST use `upsert_candidate()`. No direct INSERTs into candidates table.** This is enforced by convention, not database constraint (to keep manual NocoDB edits possible).

The full SQL is in `SOLVVE_schema_v1.sql`.

---

## 4. NocoDB Views – UI for the Team

### 4.1 Core Principle

NocoDB connects directly to the Supabase PostgreSQL database. Every table in Supabase appears as a table in NocoDB. Views are just filters + sorting + field visibility on the same data.

### 4.2 Recommended Views

**For Faro (CEO/Recruiter):**

| View Name | Type | Filter | Purpose |
|-----------|------|--------|---------|
| Open Jobs | Grid | jobs.status = 'open' | Overview of open positions |
| Pipeline [Job X] | Kanban | candidate_jobs grouped by stage | Per-job candidate pipeline |
| Greybase | Grid | source contains 'greybase' | Access to CV database |
| Hot Candidates | Grid | overall_status = 'interested' | Candidates who signaled interest |
| GDPR Pending | Grid | consent_status = 'pending' | Who still needs consent? |
| Campaign Dashboard | Grid | campaigns active | Performance of all running campaigns |
| Touchpoint Log | Grid | Last 7 days | What happened when? |

**For Sourcer (Philippines):**

| View Name | Type | Filter | Purpose |
|-----------|------|--------|---------|
| Research Tasks | Grid | Assigned jobs | What needs to be researched? |
| Longlist [Job X] | Grid | candidate_jobs.stage = 'longlist' | Research results |
| Companies [Niche X] | Grid | By industry/tech stack | Target companies for research |

**For Recruiter (Egypt):**

| View Name | Type | Filter | Purpose |
|-----------|------|--------|---------|
| My Pipeline | Kanban | Assigned candidates | Active processes |
| Call List Today | Grid | Status 'briefing_scheduled' + phone number available | Who to call? |
| Follow-ups | Grid | Last activity > 5 days ago | Who needs follow-up? |

### 4.3 Color Coding in NocoDB

| Color | Meaning |
|-------|---------|
| 🔵 Blue | Greybase (no consent, sourcing data only) |
| 🟡 Yellow | Contacted, consent pending |
| 🟢 Green | Consent granted – full ATS candidate |
| 🔴 Red | Consent refused / Do Not Contact |
| 🟣 Purple | LinkedIn contact (not yet approached) |

---

## 5. Implementation – Phases & Priorities

### Phase 0: Foundation (Week 1-2) 🔴 IMMEDIATE

**Goal:** Dev can start, data model is in place, first views usable. AND: one position worked end-to-end manually.

| # | Task | Who | Tool | Duration |
|---|------|-----|------|----------|
| **0.0** | **⚠️ BLOCKER: Check Greybase embedding dimensions** (see below) | Dev | Supabase SQL | 10 minutes |
| 0.1 | Execute SQL schema (`SOLVVE_schema_v1.sql` – tables, indexes, constraints, stored procedures) | Dev | Supabase SQL Editor | 1 day |
| **0.1b** | **Create SQL Views for NocoDB** (included in `SOLVVE_schema_v1.sql`). v_candidates, v_pipeline, v_jobs, v_qa_review, v_hot_candidates, v_touchpoints_recent. **MUST run BEFORE connecting NocoDB.** | Dev | Supabase SQL Editor | 2 hours |
| 0.2 | Migrate existing greybase_candidates to new `candidates` schema (incl. re-embedding if needed) | Dev | SQL migration + Claude Code | 1-2 days |
| 0.3 | Import LinkedIn contacts into `candidates` via `upsert_candidate()` RPC | Dev | n8n or script | 1 day |
| 0.4 | Deduplication: LinkedIn URL match between Greybase and LinkedIn contacts (automatic via `upsert_candidate()`) | Dev | SQL + Claude Code | 1 day |
| 0.5 | Connect NocoDB to Supabase **SQL Views** (NOT raw tables), set up NocoDB views (see Section 4) | Dev | NocoDB UI | 1-2 days |
| 0.6 | Set up Smartlead account + 3 email mailboxes and start warmup | Faro | Smartlead + domain setup | 1 day setup, then 2-3 weeks warmup |
| 0.6b | Set up Resend account on consent.solvve.de for transactional consent emails | Dev | Resend + DNS | 2 hours |
| **0.7** | **MANUAL VALIDATION RUN (see Section 5a)** | **Faro** | **NocoDB + manual search** | **3-5 days parallel** |

**⚠️ TASK 0.0 – VECTOR DIMENSION CHECK (DO THIS FIRST):**
Before anything else, run this query on your existing Greybase:
```sql
SELECT vector_dims(embedding) FROM greybase_chunks LIMIT 1;
```
- If result = **1536** → old `ada-002` embeddings. You MUST re-embed all 1,200 CVs with `text-embedding-3-large` (3072 dim) before any matching will work. Cost: <$1, runtime: minutes. Add this to Task 0.2.
- If result = **3072** → you're already on `text-embedding-3-large`. No action needed.
- **If you skip this, ALL pgVector matching between jobs and candidates will fail with a dimension mismatch error.** This is not a nice-to-have check.

**⚠️ TASK 0.7 IS NON-NEGOTIABLE.** Before any automation is built, Faro must work one real position end-to-end through the system manually. This validates the data model, the views, the sourcing waterfall, and the outreach sequence. One placement is worth more than 10 automated workflows. Details in Section 5a.

**⚠️ EMAIL WARMUP – START IMMEDIATELY:**
Email mailboxes need 2-3 weeks of warmup before they can be used for outbound. This means: buy/set up domains and start warmup on Day 1, in parallel with everything else.

Recommendation:
- Buy 2-3 domains (e.g. solvve-career.de, solvve-talent.de) – do NOT use the main domain
- 1-2 mailboxes per domain (faro@solvve-career.de, team@solvve-talent.de)
- Configure SPF, DKIM, DMARC correctly
- Activate Smartlead warmup feature (automatically sends emails between own mailboxes)
- After 2-3 weeks: start slowly with 10-20 emails/day, then scale up

### 5a. Manual Validation Run (Week 1, parallel to Phase 0) 🔴 CRITICAL

**Why this exists:** Every automation is a bet on assumptions. The manual run turns assumptions into data. It also generates the first revenue while the dev builds infrastructure.

**⚡ DAY-ZERO-REVENUE PLAY (before NocoDB is even ready):**
```
1. Export Greybase as CSV (today, takes 5 minutes)
2. Upload to Claude: "Tag each candidate as A/B/C for this job description: [paste JD]"
3. Filter: A-candidates with phone number or email → call/email list
4. Start calling TODAY. No NocoDB, no automation, no database.
5. Parallel: Send referral messages to 50 LinkedIn connections
   (placed candidates, positive declines, industry contacts)
```
This costs zero dev time. A filtered spreadsheet is sufficient for Day 1. One placement from this pays for months of development.

**Full manual validation (once NocoDB is up, Day 2-3):**
```
1. Pick ONE open position with highest priority / quickest expected fill
2. As soon as NocoDB + basic views are up (Day 2-3):
   ├─ Search Greybase manually via NocoDB (filter by skills, title, company)
   ├─ Search LinkedIn contacts manually
   ├─ Note: what works, what's missing, what's slow
   ├─ Build longlist manually in NocoDB (candidate_jobs records)
   │
3. Start outreach MANUALLY:
   ├─ Candidates with phone → call
   ├─ Candidates with email → send personal email (not Smartlead yet, warmup ongoing)
   ├─ LinkedIn → Connection request / message via Expandi
   │
4. Document EVERYTHING:
   ├─ How many candidates in Greybase matched? Quality?
   ├─ How many had phone/email? → Validates contact data coverage
   ├─ What searches worked on LinkedIn Recruiter / Juicebox?
   ├─ What was the response rate per channel?
   ├─ Where did the process break or feel wrong?
   │
5. After 1-2 weeks: Use findings to adjust:
   ├─ Schema fields that are actually needed vs. theoretical
   ├─ NocoDB views that are useful vs. unused
   ├─ Which automation would save the most time (build THAT first)
```

**Output:** A written "Lessons Learned" doc (even just bullet points) that feeds directly into Phase 1 prioritization. Plus: candidates in the pipeline generating revenue.

### 5b. QA Process – Sourcer Quality Control

**Problem:** When Philippines sourcer starts adding candidates to the database, there's no quality gate. Bad data (wrong niche, outdated profiles, duplicates) pollutes the system.

**Solution:** Add an approval step before outreach:

| Step | Who | What |
|------|-----|------|
| 1. Research | Sourcer | Finds candidates, adds to NocoDB with stage='longlist' and status='pending_review' |
| 2. Review | Faro / Recruiter | Checks relevance, data quality, dedup. Approves → status='approved' or rejects → status='rejected' with reason |
| 3. Outreach | Faro / Recruiter / Automation | Only 'approved' candidates enter outreach flows |

**In NocoDB:** Add a "QA Review" view filtered on `status='pending_review'`. Sourcer cannot change status to 'approved' (field permission in NocoDB or enforced via n8n).

**Phase-out:** Once sourcer quality is consistently high (after ~4-6 weeks), reduce review to spot checks (every 5th candidate).

### Phase 1: Core Workflows (Week 2-4) 🟡 PRIORITY

**Goal:** A new job can flow from Attio through to outreach.

| # | Task | Description | Tool |
|---|------|-------------|------|
| 1.1 | **Attio → Supabase Flow** | Attio **native Automation** (trigger: Deal Created → action: Send Webhook) → n8n → INSERT into `jobs` table via `upsert_candidate()` pattern | Attio UI + n8n |
| 1.2 | **Job Description Parser** | If URL: HTTP Request + HTML Extract (or Firecrawl). If PDF: Textkernel or Claude API. Result: extract `job_description_text`, key_skills, regulatory_context, tech_stack → `jobs.metadata` JSONB | n8n + Claude API / Langdock |
| 1.3 | **Create Job Embedding** | `job_description_text` → OpenAI Embedding API → `jobs.embedding` | n8n |
| 1.4 | **Greybase Matching** | pgVector similarity search: `SELECT * FROM candidates ORDER BY embedding <=> $job_embedding LIMIT 50` + filter by skills/regulatory_context | n8n + Supabase |
| 1.5 | **Matching Report** | Result as structured list: candidate, match score, contact data availability, recommended channel. Output to Faro via Langdock/email/NocoDB view | n8n + Claude API |
| 1.6 | **Dedup via `upsert_candidate()` RPC** | Every import calls the stored procedure (see Section 3.3). n8n just needs one Supabase RPC node per import flow. No sub-workflow needed. | n8n + Supabase RPC |
| 1.7 | **GDPR Consent Flow** | Send consent email (Hays model: click link = consent, opt-out anytime). Consent link → Supabase Edge Function → update `consent_status`. **Use Resend on consent.solvve.de, NOT Smartlead** (transactional vs. outbound separation). | n8n + Resend + Supabase Edge Function |

**Detail on 1.1 – Attio → Supabase:**

Attio has **native Automations** (no external setup needed). This is a 10-minute UI configuration, not a dev task:

```
Setup (in Attio UI):
├─ Create Automation: Trigger = "When Deal is created" (or "Deal moves to Active")
├─ Action = "Send Webhook" → URL: https://your-n8n.sliplane.app/webhook/attio-deal
└─ Payload includes: deal_id, client_name, job_title, custom fields

n8n receives the webhook:
├─ Extract: deal_id, client_name, job_title, job_description_url
├─ INSERT INTO jobs (attio_deal_id, client_name, job_title, job_description_url, stage='intake')
├─ IF url present → Trigger Flow 1.2 (Job Description Parser)
└─ IF pdf present → Upload to Supabase Storage → Trigger Flow 1.2
```

**Why not defer this:** At 3-5 jobs/month, manual NocoDB entry would be fine. But with Attio native automations, the webhook setup is ~2 hours total (Attio 10 min + n8n webhook node 1h + testing). This ensures every deal automatically exists in Supabase with the correct `attio_deal_id` link. Worth doing in Week 2.

**Detail on 1.7 – GDPR Consent Flow:**
```
Trigger: Candidate is moved to stage "contacted" or "briefing"
│
├─ IF consent_status = 'none':
│   ├─ Generate unique consent token (UUID)
│   ├─ Store token in candidates.consent_token
│   ├─ Send email via Smartlead/Resend:
│   │   "Hello [Name], we contacted you regarding [Job].
│   │    To process your data in compliance with GDPR, we ask for your consent:
│   │    [LINK: https://consent.solvve.de/grant/{token}]
│   │    You can revoke your consent at any time:
│   │    [LINK: https://consent.solvve.de/revoke/{token}]"
│   │
│   └─ Set consent_status = 'pending'
│
├─ Supabase Edge Function /grant/{token}:
│   ├─ UPDATE candidates SET consent_status='granted', consent_granted_at=NOW()
│   └─ Redirect to "Thank you" page
│
└─ Supabase Edge Function /revoke/{token}:
    ├─ UPDATE candidates SET consent_status='revoked', consent_revoked_at=NOW()
    └─ Redirect to "Data deleted" page (+ trigger deletion/anonymization logic)
```

### Phase 2: Outreach Integration (Week 4-6) 🟡

**Goal:** Multi-channel outreach is running, results flow back.

| # | Task | Description |
|---|------|-------------|
| 2.1 | **Expandi Webhooks → Supabase** | Connection accepted, message replied, etc. → n8n → INSERT into `touchpoints` + UPDATE `candidates.overall_status` |
| 2.2 | **Smartlead Webhooks → Supabase** | Email opened, replied, bounced → n8n → INSERT into `touchpoints` |
| 2.3 | **Smartlead Reply Handling** | When candidate replies to email: Smartlead catches the reply (via catch-all or BCC). Webhook to n8n → touchpoint with direction='inbound' + notification to Faro |
| 2.4 | **Expandi Export → Supabase** | LinkedIn Recruiter search results → Expandi → via API/webhook → n8n → dedup flow → `candidates` |
| 2.5 | **Juicebox Export → Supabase** | CSV export from Juicebox → n8n file trigger or manual upload → dedup flow → `candidates` |
| 2.6 | ~~**Campaign Stats Aggregation**~~ | **DEFERRED.** At <10 campaigns, use Expandi and Smartlead dashboards directly. Build aggregation when running 10+ simultaneous campaigns. Saves 1-2 dev days. |

**Detail on Reply Handling (2.3):**
Smartlead manages replies in its own tool. Flow:
1. Candidate replies to email → reply lands in Smartlead
2. Smartlead webhook fires to n8n with reply content
3. n8n: Match reply to candidate (via email address)
4. INSERT into `touchpoints` (channel='email', direction='inbound', message_content=reply)
5. If reply positive (AI classification via Claude API): `overall_status` → 'interested', notification to Faro
6. If reply negative/decline: `overall_status` → 'not_interested'

**Faro still needs to answer replies in Smartlead or via email client** – NocoDB is not an email client. Touchpoints in Supabase serve as overview and training data.

**⚠️ Reply content handling:** Do NOT try to parse full HTML email threads into NocoDB. Email signatures, reply chains, and HTML formatting will create a parsing nightmare. Log only: plaintext body (first 500 chars) OR just a "replied" flag + link to Smartlead conversation. Keep it simple.

### Phase 3: Enrichment & Intelligence (Week 6-10) 🟢

| # | Task | Description |
|---|------|-------------|
| 3.1 | **LinkedIn contacts via Apify enrichment** | Apify LinkedIn Profile Scraper → n8n → dedup flow → `candidates` (current_title, current_company, skills, etc.) |
| 3.2 | **Apollo.io Enrichment** | For candidates without email/phone: Apollo API → n8n → UPDATE candidates |
| 3.3 | **CSV List Import** | Old Expandi/Apollo CSV lists: n8n flow with CSV parse → dedup flow → `candidates`. ONLY import if relevant for current/planned searches |
| 3.4 | **tl;dv → Profile Enrichment** | After briefing call: tl;dv transcript → Claude API → summary → UPDATE `candidates.profile_summary` |
| 3.5 | **Stepstone Application Intake** | **SIMPLIFIED:** New Stepstone application → forward email to n8n → create candidate via `upsert_candidate()` with source='stepstone', consent_status='granted' (they applied!). Manual matching against open jobs sufficient at low volume. Automated pgVector matching deferred to Phase 4. |
| 3.6 | **Company Watchlist (Manual)** | **NO theirstack/scrapers needed yet.** Manually enter 30-50 key companies in NocoDB (Big4 FS practices, top BaFin banks/insurers, ServiceNow partners). Set up free LinkedIn Job Alerts per company. This IS the company intelligence for Phase 1-3. Automate when tracking >100 companies. |
| 3.7 | **Langdock as Analysis Interface** | Langdock Custom Assistant with Supabase access (via API plugin or function calling): "Show me all candidates with DORA experience in Hamburg" → natural language queries |

### Phase 4: Learning & Optimization (from Month 3) 🔵

| # | Task | Description |
|---|------|-------------|
| 4.1 | **Messaging Agent** | Claude API analyzes campaign data: Which message templates have the highest reply rate per candidate type? → Suggestions for new campaigns |
| 4.2 | **Research Agent** | On new job: Automatically generate boolean operators based on historical searches + results |
| 4.3 | **Candidate Scoring** | AI-based match score per candidate × job: vector similarity + enrichment data + historical response data |
| 4.4 | **Nurture Automation** | Candidates with status "not now, but later": Automatic touchpoint every 8-12 weeks (content email, job update, etc.) |

---

## 6. Sourcing Waterfall – The Operational Flow per Job

```
JOB COMES IN (Attio Deal)
│
▼
AUTOMATIC (n8n)
├─ Create job in Supabase
├─ Parse job description + create embedding
├─ pgVector match against entire candidates table
└─ Report: Top matches with contact data status
│
▼
PRIORITY 1: FREE DIRECT CONTACTS
├─ Greybase matches with phone number → CALL
├─ LinkedIn contacts with phone number → CALL
├─ Greybase matches with email → EMAIL (via Smartlead)
└─ LinkedIn contacts with email → EMAIL (via Smartlead)
│
▼
PRIORITY 1b: REFERRALS (3-5x higher conversion than cold outreach!)
├─ Previously placed candidates → "Know anyone who might be interested?"
├─ Positive declines (said no to past roles) → "This one might fit better"
├─ Industry contacts from 5,000 LinkedIn connections → warm intro request
├─ Track in Supabase: source='referral', source_details.referred_by
└─ Referral candidates skip cold outreach → direct phone/email
│
▼
PRIORITY 2: RESEARCH & SEARCH
├─ Generate boolean operators (Claude API)
├─ Juicebox search → export → dedup → Supabase
├─ LinkedIn Recruiter search → directly into Expandi
└─ Identify colleagues: former employers of longlist candidates
│       → Companies with same tech stack / same regulatory requirements
│       → Service providers and partners (e.g. ServiceNow partners)
│
▼
PRIORITY 3: MULTI-CHANNEL OUTREACH (Expandi + Smartlead)
├─ If email available: 2-3 emails via Smartlead first
│   └─ No reply → normal Expandi campaign flow
├─ If no email: Expandi campaign
│   ├─ Connection request
│   ├─ Profile visit
│   ├─ Another profile visit
│   ├─ If accepted: Message → Book call → Request CV
│   └─ If not accepted: InMail (only for high-priority)
│
▼
AFTER CONTACT
├─ Briefing call booked → tl;dv recording → profile enriched
├─ CV received → Textkernel parse → embedding → Supabase
├─ GDPR consent email automatically
├─ Move candidate to pipeline stage (NocoDB Kanban)
└─ All touchpoints + results → back into Supabase
```

### 6.1 Outreach Timing Rules (Candidate Experience)

Multi-channel outreach at senior FS profiles must be carefully timed. These people get recruiter spam daily. Standing out means being respectful, not aggressive.

**Hard Rules:**

| Rule | Rationale |
|------|-----------|
| Minimum 3 business days between channels | Email Monday → LinkedIn Thursday earliest. Never same day. |
| Maximum 2 channels active simultaneously | Email + LinkedIn OR Phone + Email. Never all three at once. |
| Clear opt-out in every touchpoint | Every email has unsubscribe. Every LinkedIn message offers "not interested? no problem." |
| No outreach on weekends | FS sector is conservative. Respect boundaries. |
| Stop all channels immediately on reply | If candidate replies on email, pause LinkedIn sequence. Handle in one channel. |
| Maximum 3 unreplied touchpoints per channel | After 3 emails without reply → stop email, try different channel OR move to "not_interested" |
| Phone: max 2 attempts, then leave voicemail or switch to written | Don't stalk. |

**Sequence Template (email available):**
```
Day 0:  Email 1 (personal, short, specific job mention)
Day 3:  Email 2 (follow-up, different angle or value prop)
Day 7:  Email 3 (final, soft close: "I understand if timing isn't right")
Day 10: LinkedIn Connection Request (if no email reply)
Day 14: LinkedIn Message (if connected) or InMail (if high-priority)
```

**Sequence Template (no email):**
```
Day 0:  Connection Request via Expandi
Day 2:  Profile Visit
Day 5:  Another Profile Visit
Day 7:  If accepted → Message with job pitch
Day 10: If accepted, no reply → Follow-up message
Day 14: If not accepted → InMail (only high-priority candidates)
```

**These rules must be configured in Expandi and Smartlead campaign settings.** They are not guidelines – they are hard constraints.

---

## 7. Email Infrastructure

### 7.1 Domain & Mailbox Setup

| Purpose | Domain | Mailboxes |
|---------|--------|-----------|
| Outbound candidates | solvve-career.de (or similar) | faro@, team@, talent@ |
| Outbound candidates 2 | solvve-talent.de (or similar) | faro@, recruiting@ |
| Consent emails | solvve.de (main domain) | consent@solvve.de (transactional, no outbound) |
| Business/clients | solvve.de | faro@solvve.de (NOT for cold outbound!) |

### 7.2 Warmup Plan

| Day | Action |
|-----|--------|
| Day 1 | Buy domains, configure DNS (SPF, DKIM, DMARC), create mailboxes |
| Day 1-3 | Add to Smartlead, activate auto-warmup |
| Week 1-2 | Smartlead warms up automatically (5-10 emails/day internally) |
| Week 3 | First real emails: 10-15/day per mailbox |
| Week 4+ | Scale up to 30-50/day per mailbox (conservative) |

### 7.3 Receiving Replies

**Problem:** When candidates reply to a Smartlead email, where does the reply land?

**Solution:** Smartlead uses the actual outbound mailboxes. Replies land in Smartlead AND in the actual mailbox. Smartlead has its own reply management ("Unibox") + webhooks.

**Flow:**
1. Reply lands in Smartlead
2. Smartlead webhook → n8n → touchpoint in Supabase
3. Faro sees the reply in Smartlead Unibox AND in NocoDB (touchpoint log)
4. Faro replies directly in Smartlead or in mail client
5. If ongoing conversation: continue via regular mail client

---

## 8. Langdock Integration

Use Langdock as a natural language interface for database queries and analysis:

**Use Cases:**

| Use Case | How |
|----------|-----|
| Candidate search | "Find all candidates with ServiceNow experience in the FS sector in Hamburg" → Langdock Custom Assistant with Supabase access (via API plugin or function calling) |
| Create job briefing | Upload job description → Langdock creates briefing for sourcer with target companies, skills, boolean operators |
| Campaign analysis | "Which Expandi campaigns had the best reply rate?" → Langdock queries campaigns table |
| Candidate summary | "Summarize the profile of [Name]" → Langdock reads from candidates + touchpoints |
| Message optimization | "Write an outreach message for senior IT auditors working at Big4, based on our best campaigns" → Langdock analyzes campaign data + writes message |

**Technical Implementation:** Create Langdock Custom Assistant with:
- System prompt with SOLVVE context (niche, target audience, tone of voice)
- API integration to Supabase REST API (read-only for security)
- Optional: n8n as middleware if Langdock doesn't have a direct Supabase connector

---

## 9. Open Questions – Resolve BEFORE Development Starts

### Technical

| # | Question | Impact |
|---|----------|--------|
| T1 | ~~Which embedding model are we using?~~ **RESOLVED:** Target is `text-embedding-3-large` (3072 dim). Check existing Greybase with Task 0.0. If 1536 (ada-002) → re-embed. Cost <$1 for 1,200 CVs. | Determines vector dimension, costs, and whether re-embedding is needed |
| T2 | Where does NocoDB run? On Sliplane (where n8n already runs) or separate server? | Hosting costs, latency |
| T3 | ~~Does Attio have webhooks or do we need to poll?~~ **RESOLVED:** Attio has **native Automations** with "Send Webhook" action. Point-and-click setup in Attio UI, 10 minutes. No polling, no custom API needed. Use trigger "When Deal is created" → action "Send Webhook" to n8n endpoint. | Determines architecture of Flow 1.1 |
| T4 | Which Apify actors for LinkedIn enrichment? Cost per profile? Rate limits? | Budget planning, timing |
| T5 | ~~Smartlead vs. Resend for consent emails~~ **RESOLVED: Use Resend (or Postmark) on consent.solvve.de subdomain.** Consent emails are transactional – mixing them with Smartlead's cold outbound infrastructure risks both deliverability and reputation. Separate domains, separate sending infrastructure. Set up in Task 0.6b. | Email flow architecture |
| T6 | NocoDB self-hosted: Docker setup on Sliplane? Or Hetzner directly? | DevOps effort |

### Operational

| # | Question | Impact |
|---|----------|--------|
| O1 | How many open positions do we have RIGHT NOW? Which have priority? | Determines which views/flows are built first |
| O2 | When do the sourcer (Philippines) and recruiter (Egypt) start? | Deadline for NocoDB views + SOPs |
| O3 | Budget for domains + Smartlead + Apify credits? | Implementation sequence |
| O4 | What does the current Expandi setup look like? Which campaigns are running? | Integration with existing setup |
| O5 | What exactly does the consent email text say? Who drafts it legally? | Must be ready before go-live |
| O6 | LinkedIn Recruiter Lite or Full? Affects available features and API access | Outreach strategy |

### Data

| # | Question | Impact |
|---|----------|--------|
| D1 | What does the current Greybase schema look like exactly? (Table structure, fields, relations) | Migration effort |
| D2 | How many of the 1,200 CVs are actually relevant (FS niche, <5 years old)? | Decides whether cleanup happens before or after migration |
| D3 | LinkedIn contacts: Available as CSV export or via API? Which fields? | Import strategy |
| D4 | How many CSV lists from Expandi/Apollo exist? Estimated volume? | Import prioritization |

---

## 9a. Revenue KPIs & Business Metrics

**Why this matters:** Without business metrics, you're measuring tool setup speed instead of business success. Define these BEFORE development starts.

**Metrics to track:**

| Metric | Target | How to measure |
|--------|--------|----------------|
| Open positions | Track count | `jobs` table, status='open' |
| Average fee per placement | Define (e.g. 20-25% of 80-100k = 16-25k) | Manual tracking in Attio |
| Outreaches per placement | Industry benchmark: 80-150 | `touchpoints` count per placed `candidate_jobs` |
| Reply rate per channel | Email: 15-25%, LinkedIn: 10-20%, Phone: 30-50% | `touchpoints` aggregation |
| Time to shortlist | Target: <5 business days from job intake | `jobs.created_at` vs first `candidate_jobs` with stage='shortlist' |
| Time to placement | Target: 4-8 weeks | `jobs.created_at` vs `candidate_jobs` with stage='placed' |
| Source quality | Which source produces most placements? | `candidates.source` × `candidate_jobs.stage='placed'` |
| Campaign ROI | Which campaigns produce interested candidates most efficiently? | `campaigns` stats vs `candidate_jobs` progression |
| Revenue pipeline | Monthly forecast | Attio deal pipeline × probability |

**Survival metric:** Define the date by which first placement revenue must arrive. Work backwards from that date to set sprint priorities.

**Dashboard:** Build a simple NocoDB Grid View called "KPI Dashboard" that shows these metrics. Most can be computed via SQL views on existing tables. Not a separate BI tool – just a NocoDB view with computed fields.

**Team Performance KPIs (weekly, per person):**

| Metric | Sourcer (PH) | Recruiter (EG) | Faro |
|--------|-------------|----------------|------|
| # new candidates added to longlist | Track | – | Review |
| # first contacts (phone + email + LinkedIn) | – | Track | Track |
| # replies received | – | Track | Track |
| # briefings scheduled | – | Track | Track |
| # candidates presented to client | – | – | Track |

Review these every Friday. If numbers are off, you know within a week – not a month.

**Using KPIs to prioritize automation:** Calculate: (outreaches needed per placement) × (open positions) = total outreach volume needed. Subtract what you can do manually today. The gap = your automation priority. If manual capacity covers 80% of the need, automate the remaining 20% – don't build a full pipeline for theoretical scale.

---

## 9b. Client-Facing Reporting

**Problem:** The document covers the full candidate lifecycle but nowhere describes how candidates are presented to clients. BaFin-regulated companies expect professional, structured deliverables.

**Candidate Profile Deliverable:**

| Section | Content | Source |
|---------|---------|--------|
| Executive Summary | 3-4 sentences on fit | Faro writes / Claude API drafts from cv_parsed + metadata |
| Current Role & Company | Title, company, duration | candidates table |
| Relevant Experience | Key positions, FS focus, regulatory exposure | cv_parsed JSONB |
| Regulatory & Tech Skills | BAIT, DORA, MaRisk, ServiceNow, etc. | metadata JSONB |
| Education & Certifications | Degrees, CISA, CIA, etc. | cv_parsed JSONB |
| Motivation & Availability | Why looking, notice period, salary expectation | profile_summary from tl;dv briefing |
| SOLVVE Assessment | Fit rating + reasoning | Faro writes |

**Format:** PDF or Word document, SOLVVE branded. Can be generated via n8n + Claude API from Supabase data in Phase 2-3.

**Minimum Viable Version (Phase 0):** Manual Word/PDF template that Faro fills in from NocoDB data. Takes 15-20 minutes per candidate. Good enough to start.

**Automated Version (Phase 3):** n8n flow triggered from NocoDB (button or stage change to 'presented'): pulls candidate data from Supabase → Claude API generates draft profile → PDF output → email to client or upload to Attio deal.

**Progress Reporting to Client:**

| Report | Frequency | Content |
|--------|-----------|---------|
| Search Kickoff | Day 1 | Understanding of requirements, target companies, timeline |
| Progress Update | Weekly | Candidates sourced, contacted, in pipeline. Blockers if any. |
| Shortlist Presentation | When ready | 3-5 candidate profiles with assessment |
| Post-Placement | After fill | Onboarding status check (30/60/90 day) |

This doesn't need automation. A structured email template is sufficient. But it must exist and be consistent.

---

## 10. Fallback Processes (when tech breaks)

**Reality:** n8n will go down. Webhooks will fail. NocoDB will have a bad day. Recruiting doesn't wait for tech fixes.

**Principle:** For every critical workflow, there must be a manual fallback that anyone on the team can execute without dev support.

| Critical Workflow | Tech Way | Manual Fallback |
|-------------------|----------|-----------------|
| New job intake | Attio webhook → n8n → Supabase | Faro creates job record directly in NocoDB |
| Greybase search | pgVector similarity search | NocoDB text search / filter on current_title + current_company |
| Candidate outreach | Expandi/Smartlead campaign | Direct LinkedIn message + manual email from business mailbox |
| Touchpoint logging | Webhooks from Expandi/Smartlead | Manual entry in NocoDB touchpoints view |
| GDPR consent | Automated consent email flow | Manual email from consent@solvve.de with consent link |
| Reply handling | Smartlead webhook → Supabase | Check Smartlead Unibox + mailbox manually, update NocoDB |
| Campaign stats | n8n cron job aggregation | Export from Expandi/Smartlead dashboard, manual update |

**Rule:** If any automated flow is broken for more than 4 hours during business hours, switch to manual fallback. Don't wait for a fix. The dev can fix it while business continues.

**Monitoring:** Set up basic uptime alerts for n8n and NocoDB (e.g. via Sliplane monitoring or a simple health check). Faro should get a Slack/email alert if n8n goes down.

**n8n Error Handling (build in Phase 1):**
- Set up a global **Error Trigger Workflow** in n8n. When any workflow crashes:
  1. Catch the error (workflow name, node, error message)
  2. Send alert to Slack/Discord/email: "Workflow X failed at Node Y. Error: Z"
  3. For data-critical flows (new applications, webhook imports): write the failed input to a `failed_jobs` table in Supabase (simple: id, workflow_name, input_payload JSONB, error_text, created_at, resolved BOOLEAN)
  4. Dev can re-trigger failed jobs manually once the issue is fixed
- This prevents silent data loss – the most dangerous failure mode in an automated pipeline.

**`failed_jobs` table:**
```sql
CREATE TABLE failed_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name TEXT NOT NULL,
    input_payload JSONB,
    error_text TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 11. Recommendations & Warnings

### Do

- **Start email domains + warmup TODAY.** This has the longest lead time. Everything else can run in parallel.
- **Run one position manually end-to-end in Week 1.** Before automating anything. This validates your process AND generates revenue. (Section 5a)
- **Complete Phase 0 in Week 1** – Deploy schema, migration, connect NocoDB. Nothing works without this.
- **Build the dedup flow FIRST** (before all imports). Every import without dedup produces chaos that's 10x more expensive to fix later.
- **Define revenue KPIs before building.** Know your survival metric: when must first placement land? (Section 9a)
- **Set up QA approval step before sourcer starts.** No unreviewed candidates entering outreach. (Section 5b)
- **Record SOPs for sourcers as Loom videos**, not documents. Show the workflow on screen.
- **Keep consent flow simple.** Hays model: email with link. No overengineering.
- **Create a manual client profile template** in Word/PDF. Automate later. (Section 9b)
- **Budget for 2-3 expert sessions** (2-4h each) for critical integration points: NocoDB↔Supabase Docker setup, n8n webhook debugging, pgVector tuning. Junior will get stuck on these. A senior freelancer for a half-day unblocks weeks of progress.

### Don't

- **Don't import all CSV lists immediately.** Only what's relevant for current jobs. The rest waits.
- **Don't try to make NocoDB an email client.** Log touchpoints yes, write emails no. That's what Smartlead is for.
- **Don't build Research Agent and Messaging Agent before Phase 4.** Collect data first, then optimize.
- **No career website now.** Irrelevant for the business model (executive search, not inbound recruiting).
- **Don't build everything at once.** Each phase must deliver standalone value.
- **Don't build campaign stats aggregation** (Flow 2.6) until running 10+ simultaneous campaigns. Use Expandi/Smartlead dashboards directly.
- **Don't build automated Stepstone matching.** Email notification + manual review sufficient at low volume.
- **Don't build theirstack/scraper integrations.** Manual company watchlist + LinkedIn Job Alerts sufficient for <50 companies.
- **Don't connect NocoDB to raw tables.** Always use SQL Views. NocoDB cannot handle JSONB filters or VECTOR columns.

### Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| NocoDB performance with many views/users | Medium | High | Monitoring, add caching layer if needed |
| Smartlead emails land in spam | High (if warmup too fast) | High | Conservative warmup, monitor via Postmaster Tools |
| Apify LinkedIn scraping: account ban | Medium | Medium | Respect rate limits, rotate proxies, don't use Faro's main account |
| Dedup errors: candidates contacted twice | High (without clean flow) | High | Build and test dedup flow first |
| Dev capacity insufficient for all phases | High | Medium | Strict phase prioritization, Claude Code for standard tasks |
| GDPR violation due to missing consent | Low | Very high | Consent flow in Phase 1, not Phase 3 |

---

## 12. Claude Code – Directly Delegatable Tasks

The following tasks can be delegated directly to Claude Code to free up the dev:

| Task | Input | Output |
|------|-------|--------|
| ~~Generate + validate SQL schema~~ | ~~This document, Section 3~~ | **DONE: `SOLVVE_schema_v1.sql`** – deploy directly in Supabase SQL Editor |
| ~~n8n dedup logic as code~~ | ~~Dedup specification (3.3)~~ | **DONE: `upsert_candidate()` stored procedure** in SQL file. n8n just calls RPC. |
| Consent page (grant/revoke) | Design spec | HTML + Supabase Edge Function code |
| Embedding pipeline | Existing Greybase code as reference | n8n workflow or Python script for job embeddings |
| Document NocoDB view configuration | Section 4.2 + SQL Views | Step-by-step guide for dev |
| Expandi webhook handler | Expandi webhook docs | n8n workflow template |
| Smartlead webhook handler | Smartlead webhook docs | n8n workflow template |
| Attio → Supabase flow | Attio Automation webhook payload + Section 4 | n8n workflow template (single webhook node + INSERT) |
| Client profile template | Section 9b spec | Word/PDF template + Claude API prompt for auto-generation |
| KPI dashboard SQL views | Section 9a metrics | SQL views that NocoDB can display as computed fields |

---

## 13. Work Package Sequence – Summary

```
DAY 0:    *** DAY-ZERO-REVENUE PLAY ***
          Export Greybase CSV → Claude batch-tag for priority position → call A-candidates
          Send referral messages to 50 LinkedIn connections
          Enter 30-50 key companies in spreadsheet (watchlist)

WEEK 1:   *** CHECK GREYBASE EMBEDDING DIMENSIONS (Task 0.0) ***
          Buy email domains + start warmup
          Set up Resend on consent.solvve.de
          Deploy SQL schema incl. SQL Views (SOLVVE_schema_v1.sql)
          Greybase migration to new schema (re-embed if 1536 dim)
          Connect NocoDB to SQL Views (NOT raw tables)
          *** START MANUAL VALIDATION RUN on priority position ***

WEEK 2:   Continue manual validation → first outreach happening
          Import LinkedIn contacts via upsert_candidate() RPC
          Attio native Automation → n8n webhook → Supabase (Flow 1.1)

WEEK 3:   Job description parser (Flow 1.2)
          Job embedding + Greybase matching (Flow 1.3/1.4)
          GDPR consent flow (Flow 1.7) – via Resend, not Smartlead
          n8n global error workflow + failed_jobs table
          Manual validation: document lessons learned → adjust priorities

WEEK 4:   Expandi webhooks → Supabase (Flow 2.1)
          Smartlead webhooks → Supabase (Flow 2.2)
          Reply handling (Flow 2.3) – plaintext only, no HTML parsing
          First real campaign with full data flow

WEEK 5-6: Apify LinkedIn enrichment
           Apollo enrichment for missing contact data
           Juicebox export → Supabase flow via upsert_candidate()
           Views for sourcer/recruiter + SOPs + QA process
           Client profile template (manual version)

MONTH 3+: Stepstone application intake (simplified)
           Company watchlist → NocoDB (manual)
           Langdock integration
           Campaign analytics (when >10 campaigns)
           Automated client profile generation
```

---

## Appendix: Toolstack Reference

| Tool | Purpose | Cost (approx.) | Priority |
|------|---------|----------------|----------|
| Supabase | PostgreSQL + pgVector + Edge Functions + Storage | Free-$25/month | ⬛ In place |
| NocoDB | UI on Supabase | Self-hosted, free | ⬛ Phase 0 |
| n8n | Workflow orchestration | Self-hosted on Sliplane | ⬛ In place |
| Attio | CRM/BD | Existing subscription | ⬛ In place |
| Expandi | LinkedIn outreach | ~$99/month | ⬛ In place |
| Smartlead | Email outreach + warmup | ~$39-94/month | 🟡 Phase 1 |
| Resend | Transactional emails (GDPR consent) | Free-$20/month | 🟡 Phase 0 (Task 0.6b) |
| LinkedIn Recruiter | Candidate search | Existing subscription | ⬛ In place |
| Juicebox | AI-based candidate search | Existing subscription | ⬛ In place |
| Stepstone Direct | Candidate database | Existing subscription | ⬛ In place |
| Textkernel | CV parsing | Pay-per-use | ⬛ In place |
| Apollo.io | Contact data enrichment | Free-$49/month | ⬛ In place |
| Apify | LinkedIn profile scraping | ~$49/month | 🟡 Phase 3 |
| tl;dv | Interview recording + transcription | Free-$25/month | ⬛ In place |
| Langdock | AI assistants + LLM access for team | Existing subscription | 🟢 Phase 3 |
| Claude API | Embedding, parsing, agents | Pay-per-use | 🟡 Phase 1 |
| theirstack | Company intelligence / job scraping | TBD | 🔵 Phase 4+ (when >100 companies) |

---

*This document is the working foundation. It will be iteratively expanded. Each phase will be documented with lessons learned upon completion.*

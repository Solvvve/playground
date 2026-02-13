-- =============================================================================
-- Migration: Candidate Sync & Deduplication Functions
-- Created: 2026-02-13
-- 
-- Three RPC functions that keep the unified `candidates` table in sync
-- with the source tables (`expandi_network`, `textkernel_resumes`).
--
-- Dedup cascade for expandi:
--   1. expandi_id (already linked)
--   2. linkedin_url match
--   3. email match (case-insensitive)
--
-- Dedup cascade for textkernel:
--   1. textkernel_id (already linked)
--   2. email match (case-insensitive)
--   3. first_name + last_name match
-- =============================================================================

-- sync_expandi_to_candidates: Dedup and merge expandi contact into candidates
CREATE OR REPLACE FUNCTION sync_expandi_to_candidates(p_expandi_id BIGINT)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_expandi RECORD;
    v_candidate_id UUID;
    v_match_method TEXT;
BEGIN
    SELECT * INTO v_expandi FROM expandi_network WHERE id = p_expandi_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'expandi_network row % not found', p_expandi_id;
    END IF;

    -- Check 1: Already linked by expandi_id
    SELECT id INTO v_candidate_id FROM candidates WHERE expandi_id = p_expandi_id;
    IF FOUND THEN
        UPDATE candidates SET
            first_name      = COALESCE(candidates.first_name, v_expandi.first_name),
            last_name       = COALESCE(candidates.last_name, v_expandi.last_name),
            email           = COALESCE(candidates.email, v_expandi.email),
            phone           = COALESCE(candidates.phone, v_expandi.phone),
            linkedin_url    = COALESCE(candidates.linkedin_url, v_expandi.profile_link),
            current_title   = COALESCE(v_expandi.job_title, candidates.current_title),
            current_company = COALESCE(v_expandi.company_name, candidates.current_company),
            location        = COALESCE(v_expandi.location, candidates.location),
            contact_status  = v_expandi.contact_status,
            conversation_status = v_expandi.conversation_status,
            concat_tags     = v_expandi.concat_tags,
            connected_at    = COALESCE(v_expandi.connected_at, candidates.connected_at),
            invited_at      = COALESCE(v_expandi.invited_at, candidates.invited_at),
            image_link      = COALESCE(candidates.image_link, v_expandi.image_link),
            updated_at      = NOW()
        WHERE id = v_candidate_id;
        RETURN v_candidate_id;
    END IF;

    -- Check 2: LinkedIn URL match
    IF v_expandi.profile_link IS NOT NULL THEN
        SELECT id INTO v_candidate_id
        FROM candidates
        WHERE linkedin_url = v_expandi.profile_link;
        IF FOUND THEN
            v_match_method := 'linkedin';
        END IF;
    END IF;

    -- Check 3: Email match (case-insensitive)
    IF v_candidate_id IS NULL AND v_expandi.email IS NOT NULL THEN
        SELECT id INTO v_candidate_id
        FROM candidates
        WHERE LOWER(email) = LOWER(v_expandi.email);
        IF FOUND THEN
            v_match_method := 'email';
        END IF;
    END IF;

    -- Match found: merge
    IF v_candidate_id IS NOT NULL THEN
        UPDATE candidates SET
            first_name      = COALESCE(candidates.first_name, v_expandi.first_name),
            last_name       = COALESCE(candidates.last_name, v_expandi.last_name),
            email           = COALESCE(candidates.email, v_expandi.email),
            phone           = COALESCE(candidates.phone, v_expandi.phone),
            linkedin_url    = COALESCE(candidates.linkedin_url, v_expandi.profile_link),
            current_title   = COALESCE(v_expandi.job_title, candidates.current_title),
            current_company = COALESCE(v_expandi.company_name, candidates.current_company),
            location        = COALESCE(v_expandi.location, candidates.location),
            contact_status  = v_expandi.contact_status,
            conversation_status = v_expandi.conversation_status,
            concat_tags     = v_expandi.concat_tags,
            connected_at    = COALESCE(v_expandi.connected_at, candidates.connected_at),
            invited_at      = COALESCE(v_expandi.invited_at, candidates.invited_at),
            image_link      = COALESCE(candidates.image_link, v_expandi.image_link),
            source          = 'both',
            expandi_id      = p_expandi_id,
            match_method    = v_match_method,
            updated_at      = NOW()
        WHERE id = v_candidate_id;
        RETURN v_candidate_id;
    END IF;

    -- No match: insert new candidate
    INSERT INTO candidates (
        first_name, last_name, email, phone, linkedin_url,
        current_title, current_company, location,
        contact_status, conversation_status, concat_tags,
        connected_at, invited_at, image_link,
        source, expandi_id, match_method,
        created_at, updated_at
    ) VALUES (
        v_expandi.first_name, v_expandi.last_name, v_expandi.email, v_expandi.phone, v_expandi.profile_link,
        v_expandi.job_title, v_expandi.company_name, v_expandi.location,
        v_expandi.contact_status, v_expandi.conversation_status, v_expandi.concat_tags,
        v_expandi.connected_at, v_expandi.invited_at, v_expandi.image_link,
        'expandi', p_expandi_id, NULL,
        NOW(), NOW()
    )
    RETURNING id INTO v_candidate_id;

    RETURN v_candidate_id;
END;
$$;


-- sync_textkernel_to_candidates: Dedup and merge textkernel resume into candidates
CREATE OR REPLACE FUNCTION sync_textkernel_to_candidates(p_textkernel_id UUID)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_resume RECORD;
    v_contact RECORD;
    v_email TEXT;
    v_phone TEXT;
    v_current_title TEXT;
    v_current_company TEXT;
    v_location TEXT;
    v_skills TEXT;
    v_candidate_id UUID;
    v_match_method TEXT;
BEGIN
    SELECT * INTO v_resume FROM textkernel_resumes WHERE id = p_textkernel_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'textkernel_resumes row % not found', p_textkernel_id;
    END IF;

    SELECT * INTO v_contact FROM textkernel_contact WHERE resume_id = p_textkernel_id;

    SELECT e.email INTO v_email
    FROM textkernel_emails e
    WHERE e.resume_id = p_textkernel_id
    ORDER BY e.id LIMIT 1;

    SELECT normalized INTO v_phone
    FROM textkernel_phones
    WHERE resume_id = p_textkernel_id
    ORDER BY id LIMIT 1;

    SELECT job_title_raw, employer_name_raw
    INTO v_current_title, v_current_company
    FROM textkernel_positions
    WHERE resume_id = p_textkernel_id
    ORDER BY is_current DESC NULLS LAST, end_date DESC NULLS FIRST, start_date DESC NULLS LAST
    LIMIT 1;

    IF v_contact IS NOT NULL THEN
        v_location := CONCAT_WS(', ',
            NULLIF(v_contact.municipality, ''),
            NULLIF(ARRAY_TO_STRING(v_contact.regions, ', '), ''),
            NULLIF(v_contact.country_code, '')
        );
        IF v_location = '' THEN v_location := NULL; END IF;
    END IF;

    SELECT STRING_AGG(normalized_name, ', ' ORDER BY normalized_name)
    INTO v_skills
    FROM (
        SELECT normalized_name
        FROM textkernel_skills
        WHERE resume_id = p_textkernel_id AND normalized_name IS NOT NULL
        LIMIT 20
    ) sub;

    -- Check 1: Already linked by textkernel_id
    SELECT id INTO v_candidate_id FROM candidates WHERE textkernel_id = p_textkernel_id;
    IF FOUND THEN
        UPDATE candidates SET
            first_name              = COALESCE(candidates.first_name, v_contact.given_name),
            last_name               = COALESCE(candidates.last_name, v_contact.family_name),
            email                   = COALESCE(candidates.email, v_email),
            phone                   = COALESCE(candidates.phone, v_phone),
            current_title           = COALESCE(v_current_title, candidates.current_title),
            current_company         = COALESCE(v_current_company, candidates.current_company),
            location                = COALESCE(candidates.location, v_location),
            professional_summary    = COALESCE(v_resume.professional_summary, candidates.professional_summary),
            highest_degree          = COALESCE(v_resume.highest_degree_normalized, candidates.highest_degree),
            current_management_level = COALESCE(v_resume.current_management_level, candidates.current_management_level),
            management_score        = COALESCE(v_resume.management_score, candidates.management_score),
            months_work_experience  = COALESCE(v_resume.months_work_experience, candidates.months_work_experience),
            experience_description  = COALESCE(v_resume.experience_description, candidates.experience_description),
            skills_summary          = COALESCE(v_skills, candidates.skills_summary),
            cv_file_name            = COALESCE(v_resume.file_name, candidates.cv_file_name),
            updated_at              = NOW()
        WHERE id = v_candidate_id;
        RETURN v_candidate_id;
    END IF;

    -- Check 2: Email match
    IF v_email IS NOT NULL THEN
        SELECT id INTO v_candidate_id
        FROM candidates
        WHERE LOWER(email) = LOWER(v_email);
        IF FOUND THEN
            v_match_method := 'email';
        END IF;
    END IF;

    -- Check 3: Name match (first + last, both non-null)
    IF v_candidate_id IS NULL
       AND v_contact IS NOT NULL
       AND v_contact.given_name IS NOT NULL
       AND v_contact.family_name IS NOT NULL
    THEN
        SELECT id INTO v_candidate_id
        FROM candidates
        WHERE LOWER(first_name) = LOWER(v_contact.given_name)
          AND LOWER(last_name) = LOWER(v_contact.family_name)
        LIMIT 1;
        IF FOUND THEN
            v_match_method := 'name';
        END IF;
    END IF;

    -- Match found: merge
    IF v_candidate_id IS NOT NULL THEN
        UPDATE candidates SET
            first_name              = COALESCE(candidates.first_name, v_contact.given_name),
            last_name               = COALESCE(candidates.last_name, v_contact.family_name),
            email                   = COALESCE(candidates.email, v_email),
            phone                   = COALESCE(candidates.phone, v_phone),
            current_title           = COALESCE(v_current_title, candidates.current_title),
            current_company         = COALESCE(v_current_company, candidates.current_company),
            location                = COALESCE(candidates.location, v_location),
            professional_summary    = COALESCE(v_resume.professional_summary, candidates.professional_summary),
            highest_degree          = COALESCE(v_resume.highest_degree_normalized, candidates.highest_degree),
            current_management_level = COALESCE(v_resume.current_management_level, candidates.current_management_level),
            management_score        = COALESCE(v_resume.management_score, candidates.management_score),
            months_work_experience  = COALESCE(v_resume.months_work_experience, candidates.months_work_experience),
            experience_description  = COALESCE(v_resume.experience_description, candidates.experience_description),
            skills_summary          = COALESCE(v_skills, candidates.skills_summary),
            cv_file_name            = COALESCE(v_resume.file_name, candidates.cv_file_name),
            source                  = 'both',
            textkernel_id           = p_textkernel_id,
            match_method            = v_match_method,
            updated_at              = NOW()
        WHERE id = v_candidate_id;
        RETURN v_candidate_id;
    END IF;

    -- No match: insert new candidate
    INSERT INTO candidates (
        first_name, last_name, email, phone,
        current_title, current_company, location,
        professional_summary, highest_degree,
        current_management_level, management_score,
        months_work_experience, experience_description,
        skills_summary, cv_file_name,
        source, textkernel_id, match_method,
        created_at, updated_at
    ) VALUES (
        v_contact.given_name, v_contact.family_name, v_email, v_phone,
        v_current_title, v_current_company, v_location,
        v_resume.professional_summary, v_resume.highest_degree_normalized,
        v_resume.current_management_level, v_resume.management_score,
        v_resume.months_work_experience, v_resume.experience_description,
        v_skills, v_resume.file_name,
        'textkernel', p_textkernel_id, NULL,
        NOW(), NOW()
    )
    RETURNING id INTO v_candidate_id;

    RETURN v_candidate_id;
END;
$$;


-- upsert_expandi_candidate: Full pipeline - upsert into expandi_network then sync to candidates
CREATE OR REPLACE FUNCTION upsert_expandi_candidate(payload JSONB)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_expandi_id BIGINT;
    v_candidate_id UUID;
BEGIN
    INSERT INTO expandi_network (
        id, first_name, last_name, email, phone, address,
        profile_link, public_identifier, profile_link_public_identifier,
        image_link, object_urn, job_title, company_name,
        company_universal_name, company_website,
        employee_count_start, employee_count_end,
        industries, location, follower_count,
        contact_status, conversation_status, thread,
        invited_at, connected_at, concat_tags, owned_by,
        source_file, source, updated_at
    ) VALUES (
        (payload->>'id')::BIGINT,
        payload->>'first_name',
        payload->>'last_name',
        payload->>'email',
        payload->>'phone',
        payload->>'address',
        payload->>'profile_link',
        payload->>'public_identifier',
        payload->>'profile_link_public_identifier',
        payload->>'image_link',
        (payload->>'object_urn')::BIGINT,
        payload->>'job_title',
        payload->>'company_name',
        payload->>'company_universal_name',
        payload->>'company_website',
        (payload->>'employee_count_start')::INTEGER,
        (payload->>'employee_count_end')::INTEGER,
        payload->>'industries',
        payload->>'location',
        (payload->>'follower_count')::INTEGER,
        payload->>'contact_status',
        payload->>'conversation_status',
        payload->>'thread',
        (payload->>'invited_at')::TIMESTAMPTZ,
        (payload->>'connected_at')::TIMESTAMPTZ,
        payload->>'concat_tags',
        payload->>'owned_by',
        payload->>'source_file',
        payload->>'source',
        NOW()
    )
    ON CONFLICT (id) DO UPDATE SET
        first_name      = COALESCE(EXCLUDED.first_name, expandi_network.first_name),
        last_name       = COALESCE(EXCLUDED.last_name, expandi_network.last_name),
        email           = COALESCE(EXCLUDED.email, expandi_network.email),
        phone           = COALESCE(EXCLUDED.phone, expandi_network.phone),
        address         = COALESCE(EXCLUDED.address, expandi_network.address),
        profile_link    = COALESCE(EXCLUDED.profile_link, expandi_network.profile_link),
        image_link      = COALESCE(EXCLUDED.image_link, expandi_network.image_link),
        object_urn      = COALESCE(EXCLUDED.object_urn, expandi_network.object_urn),
        job_title       = COALESCE(EXCLUDED.job_title, expandi_network.job_title),
        company_name    = COALESCE(EXCLUDED.company_name, expandi_network.company_name),
        location        = COALESCE(EXCLUDED.location, expandi_network.location),
        contact_status  = COALESCE(EXCLUDED.contact_status, expandi_network.contact_status),
        conversation_status = COALESCE(EXCLUDED.conversation_status, expandi_network.conversation_status),
        concat_tags     = COALESCE(EXCLUDED.concat_tags, expandi_network.concat_tags),
        connected_at    = COALESCE(EXCLUDED.connected_at, expandi_network.connected_at),
        invited_at      = COALESCE(EXCLUDED.invited_at, expandi_network.invited_at),
        updated_at      = NOW()
    RETURNING id INTO v_expandi_id;

    v_candidate_id := sync_expandi_to_candidates(v_expandi_id);
    RETURN v_candidate_id;
END;
$$;

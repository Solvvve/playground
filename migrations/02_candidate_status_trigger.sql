-- Migration: candidate_status_change_trigger
-- Logs candidate additions and status changes to job_activities automatically.

-- Trigger function: log candidate_status changes to job_activities
CREATE OR REPLACE FUNCTION log_candidate_status_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Only fire on actual status changes, not on non-status updates
    IF TG_OP = 'UPDATE' AND OLD.candidate_status IS DISTINCT FROM NEW.candidate_status THEN
        INSERT INTO public.job_activities (
            job_id,
            activity_type,
            content,
            created_by,
            metadata
        ) VALUES (
            NEW.job_id,
            'candidate_update',
            'Candidate status changed from "' || OLD.candidate_status || '" to "' || NEW.candidate_status || '"',
            current_user,
            jsonb_build_object(
                'candidate_id', NEW.candidate_id,
                'old_status', OLD.candidate_status,
                'new_status', NEW.candidate_status
            )
        );
    END IF;

    -- Also log when a candidate is first added to a job
    IF TG_OP = 'INSERT' THEN
        INSERT INTO public.job_activities (
            job_id,
            activity_type,
            content,
            created_by,
            metadata
        ) VALUES (
            NEW.job_id,
            'candidate_update',
            'Candidate added to job with status "' || NEW.candidate_status || '"',
            current_user,
            jsonb_build_object(
                'candidate_id', NEW.candidate_id,
                'status', NEW.candidate_status
            )
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger to job_candidates
CREATE TRIGGER trg_candidate_status_change
    AFTER INSERT OR UPDATE ON public.job_candidates
    FOR EACH ROW
    EXECUTE FUNCTION log_candidate_status_change();

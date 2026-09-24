# -*- coding: utf-8 -*-
import subprocess

sql_command = """
DO $$
DECLARE
    q_id INT;
    target_id INT;
    moved_count INT := 0;
BEGIN
    -- Qualified stage (cast name::text for jsonb in Odoo 19)
    SELECT id INTO q_id FROM crm_stage WHERE name::text ILIKE '%qualified%' LIMIT 1;

    -- Target stage (Contacted or New Lead)
    SELECT id INTO target_id FROM crm_stage 
    WHERE (name::text ILIKE '%contacted%' OR name::text ILIKE '%new%') AND id != q_id 
    ORDER BY sequence ASC LIMIT 1;

    IF q_id IS NOT NULL AND target_id IS NOT NULL THEN
        -- Shift leads to target stage
        UPDATE crm_lead SET stage_id = target_id WHERE stage_id = q_id;
        GET DIAGNOSTICS moved_count = ROW_COUNT;

        -- Delete Qualified stage
        DELETE FROM crm_stage WHERE id = q_id;

        RAISE NOTICE '✅ Successfully moved % lead(s) to target stage (ID: %) and deleted Qualified stage (ID: %)!', moved_count, target_id, q_id;
    ELSIF q_id IS NULL THEN
        RAISE NOTICE 'ℹ️ Qualified stage not found or already deleted.';
    ELSE
        RAISE NOTICE '⚠️ Could not find a suitable target stage to move leads.';
    END IF;
END $$;
"""

cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql_command]
res = subprocess.run(cmd, capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print(res.stderr)

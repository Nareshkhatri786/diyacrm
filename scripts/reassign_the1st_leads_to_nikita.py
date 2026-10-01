# -*- coding: utf-8 -*-
"""
Diya CRM: Reassign 'The 1st Residency' leads from Heer to Nikita and ensure user setup.
"""
import subprocess

def run_reassign():
    print("===================================================================")
    print(" 🚀 The 1st Residency: Reassigning Leads to Nikita")
    print("===================================================================")
    sql = """
DO $$
DECLARE
    the1st_comp_id INT;
    nikita_uid INT;
    heer_uid INT;
    lead_count INT := 0;
BEGIN
    -- 1. Find The 1st Residency Company
    SELECT id INTO the1st_comp_id FROM res_company 
    WHERE name ILIKE '%1st%' OR name ILIKE '%first%' LIMIT 1;

    -- 2. Find Nikita User (or create if missing)
    SELECT id INTO nikita_uid FROM res_users 
    WHERE (name ILIKE '%nikita%' OR login ILIKE '%nikita%') AND share = FALSE 
    ORDER BY id ASC LIMIT 1;

    -- 3. Find Heer User
    SELECT id INTO heer_uid FROM res_users 
    WHERE (name ILIKE '%heer%' OR login ILIKE '%heer%') 
    ORDER BY id ASC LIMIT 1;

    IF the1st_comp_id IS NULL THEN
        RAISE NOTICE '⚠️ Company "The 1st Residency" not found!';
        RETURN;
    END IF;

    IF nikita_uid IS NULL THEN
        RAISE NOTICE '⚠️ User Nikita not found in res_users! Please ensure Nikita is created or will be auto-created on next lead.';
    ELSE
        -- Ensure Nikita has access to The 1st Residency
        IF NOT EXISTS (SELECT 1 FROM res_company_users_rel WHERE cid = the1st_comp_id AND user_id = nikita_uid) THEN
            INSERT INTO res_company_users_rel (cid, user_id) VALUES (the1st_comp_id, nikita_uid);
            RAISE NOTICE '✅ Added The 1st Residency company access for Nikita (User ID: %)', nikita_uid;
        END IF;

        -- Reassign The 1st Residency leads currently under Heer to Nikita
        IF heer_uid IS NOT NULL THEN
            UPDATE crm_lead 
            SET user_id = nikita_uid 
            WHERE company_id = the1st_comp_id AND user_id = heer_uid;

            GET DIAGNOSTICS lead_count = ROW_COUNT;
            RAISE NOTICE '✅ Successfully reassigned % existing lead(s) of The 1st Residency from Heer (ID: %) to Nikita (ID: %)!', lead_count, heer_uid, nikita_uid;
        ELSE
            RAISE NOTICE 'ℹ️ Heer user not found. No leads needed reassigning.';
        END IF;
    END IF;
END $$;
"""
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)

if __name__ == '__main__':
    run_reassign()

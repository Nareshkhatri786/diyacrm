# -*- coding: utf-8 -*-
"""
Diya CRM: Reassign 'The 1st Residency' leads from Heer to Nikita and ensure user setup.
"""
import os
import sys
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
    nikita_partner_id INT;
    heer_uid INT;
    heer_reassigned_count INT := 0;
    unassigned_count INT := 0;
    activity_count INT := 0;
    total_nikita_leads INT := 0;
BEGIN
    -- 1. Find The 1st Residency Company
    SELECT id INTO the1st_comp_id FROM res_company 
    WHERE name ILIKE '%1st%' OR name ILIKE '%first%' OR name ILIKE '%radhe%'
    ORDER BY id ASC LIMIT 1;

    -- 2. Find Nikita User (join res_partner because 'name' is in res_partner)
    SELECT u.id INTO nikita_uid 
    FROM res_users u
    JOIN res_partner p ON p.id = u.partner_id
    WHERE (p.name ILIKE '%nikita%' OR u.login ILIKE '%nikita%') AND u.share = FALSE 
    ORDER BY u.id ASC LIMIT 1;

    -- 3. Find Heer User (join res_partner)
    SELECT u.id INTO heer_uid 
    FROM res_users u
    JOIN res_partner p ON p.id = u.partner_id
    WHERE (p.name ILIKE '%heer%' OR u.login ILIKE '%heer%') 
    ORDER BY u.id ASC LIMIT 1;

    IF the1st_comp_id IS NULL THEN
        RAISE NOTICE '⚠️ Company "The 1st Residency" not found in res_company!';
        RETURN;
    END IF;

    -- Create Nikita partner and user if missing
    IF nikita_uid IS NULL THEN
        SELECT id INTO nikita_partner_id FROM res_partner WHERE name ILIKE 'Nikita%' LIMIT 1;
        IF nikita_partner_id IS NULL THEN
            INSERT INTO res_partner (name, email, company_id, active, type)
            VALUES ('Nikita', 'nikita@the1stresidency.com', the1st_comp_id, TRUE, 'contact')
            RETURNING id INTO nikita_partner_id;
        END IF;

        INSERT INTO res_users (login, partner_id, company_id, active, notification_type)
        VALUES ('Nikita', nikita_partner_id, the1st_comp_id, TRUE, 'email')
        RETURNING id INTO nikita_uid;

        RAISE NOTICE '✅ Created user Nikita (ID: %)', nikita_uid;
    ELSE
        RAISE NOTICE 'ℹ️ Found Nikita user (ID: %)', nikita_uid;
    END IF;

    -- Ensure Nikita has access to The 1st Residency company in res_company_users_rel
    IF NOT EXISTS (SELECT 1 FROM res_company_users_rel WHERE cid = the1st_comp_id AND user_id = nikita_uid) THEN
        INSERT INTO res_company_users_rel (cid, user_id) VALUES (the1st_comp_id, nikita_uid);
        RAISE NOTICE '✅ Added The 1st Residency company access for Nikita (User ID: %)', nikita_uid;
    END IF;

    -- Update Nikita default company_id if not set
    UPDATE res_users SET company_id = the1st_comp_id WHERE id = nikita_uid AND company_id IS NULL;

    -- 4. Set company_id for any orphan leads mentioning The 1st Residency
    UPDATE crm_lead 
    SET company_id = the1st_comp_id 
    WHERE company_id IS NULL 
      AND (name ILIKE '%1st%' OR name ILIKE '%the 1st%' OR name ILIKE '%the1st%' OR name ILIKE '%radhe%');

    -- 5. Reassign The 1st Residency leads currently under Heer to Nikita
    IF heer_uid IS NOT NULL THEN
        RAISE NOTICE 'ℹ️ Found Heer user (ID: %)', heer_uid;
        UPDATE crm_lead 
        SET user_id = nikita_uid,
            company_id = the1st_comp_id
        WHERE (company_id = the1st_comp_id OR name ILIKE '%1st%' OR name ILIKE '%the 1st%' OR name ILIKE '%the1st%')
          AND user_id = heer_uid;
        GET DIAGNOSTICS heer_reassigned_count = ROW_COUNT;

        -- Also reassign open activities from Heer to Nikita on these leads
        UPDATE mail_activity
        SET user_id = nikita_uid
        WHERE res_model = 'crm.lead'
          AND user_id = heer_uid
          AND res_id IN (
              SELECT id FROM crm_lead WHERE company_id = the1st_comp_id
          );
        GET DIAGNOSTICS activity_count = ROW_COUNT;

        RAISE NOTICE '✅ Successfully reassigned % lead(s) and % activity/activities from Heer (ID: %) to Nikita (ID: %)!', 
                     heer_reassigned_count, activity_count, heer_uid, nikita_uid;
    ELSE
        RAISE NOTICE 'ℹ️ Heer user not found in res_users.';
    END IF;

    -- 6. Also assign any unassigned or admin-assigned leads in The 1st Residency to Nikita
    UPDATE crm_lead 
    SET user_id = nikita_uid 
    WHERE company_id = the1st_comp_id AND (user_id IS NULL OR user_id IN (1, 2));
    GET DIAGNOSTICS unassigned_count = ROW_COUNT;
    IF unassigned_count > 0 THEN
        RAISE NOTICE '✅ Assigned % unassigned/admin lead(s) of The 1st Residency to Nikita (ID: %)!', unassigned_count, nikita_uid;
    END IF;

    -- 7. Total leads now assigned to Nikita
    SELECT COUNT(*) INTO total_nikita_leads FROM crm_lead WHERE user_id = nikita_uid;
    RAISE NOTICE '📊 Total leads now assigned to Nikita: %', total_nikita_leads;

END $$;
"""

    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr)

if __name__ == '__main__':
    run_reassign()

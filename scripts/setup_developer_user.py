# -*- coding: utf-8 -*-
"""
Diya CRM: Helper CLI to configure or create a Developer User (Unit Inventory Only).
Usage:
    python3 scripts/setup_developer_user.py [username_or_login]
Examples:
    python3 scripts/setup_developer_user.py dhaval
    python3 scripts/setup_developer_user.py
"""
import sys
import subprocess

def run_setup():
    target_user = sys.argv[1].strip() if len(sys.argv) > 1 else None

    if target_user:
        sql = f"""
DO $$
DECLARE
    u_id INT;
    dev_gid INT;
    matrix_action_id INT;
    sales_gid INT;
    sales_mgr_gid INT;
    att_gid INT;
    att_mgr_gid INT;
    u_name TEXT;
BEGIN
    -- 1. Find target user
    SELECT u.id, p.name INTO u_id, u_name
    FROM res_users u
    JOIN res_partner p ON p.id = u.partner_id
    WHERE u.login ILIKE '{target_user}' OR p.name ILIKE '%{target_user}%'
    LIMIT 1;

    IF u_id IS NULL THEN
        RAISE NOTICE '⚠️ User matching "{target_user}" not found in res_users!';
        RETURN;
    END IF;

    -- 2. Find Developer Group
    SELECT res_id INTO dev_gid FROM ir_model_data
    WHERE module = 'diyacrm' AND name = 'group_property_developer' LIMIT 1;

    -- 3. Find Visual Matrix Action
    SELECT res_id INTO matrix_action_id FROM ir_model_data
    WHERE module = 'diyacrm' AND name = 'action_crm_unit_matrix' LIMIT 1;

    -- 4. Find Sales & Attendance groups to remove
    SELECT res_id INTO sales_gid FROM ir_model_data WHERE module = 'sales_team' AND name = 'group_sale_salesman' LIMIT 1;
    SELECT res_id INTO sales_mgr_gid FROM ir_model_data WHERE module = 'sales_team' AND name = 'group_sale_manager' LIMIT 1;
    SELECT res_id INTO att_gid FROM ir_model_data WHERE module = 'hr_attendance' AND name = 'group_hr_attendance_user' LIMIT 1;
    SELECT res_id INTO att_mgr_gid FROM ir_model_data WHERE module = 'hr_attendance' AND name = 'group_hr_attendance_manager' LIMIT 1;

    IF dev_gid IS NOT NULL THEN
        -- Add developer group
        IF NOT EXISTS (SELECT 1 FROM res_groups_users_rel WHERE uid = u_id AND gid = dev_gid) THEN
            INSERT INTO res_groups_users_rel (uid, gid) VALUES (u_id, dev_gid);
        END IF;

        -- Remove sales & attendance groups to isolate to Unit Inventory
        DELETE FROM res_groups_users_rel WHERE uid = u_id AND gid IN (sales_gid, sales_mgr_gid, att_gid, att_mgr_gid);

        -- Set home action
        IF matrix_action_id IS NOT NULL THEN
            UPDATE res_users SET action_id = matrix_action_id WHERE id = u_id;
        END IF;

        RAISE NOTICE '✅ Successfully configured user "%" (Login: {target_user}, ID: %) as DEVELOPER (Unit Inventory Only)!', u_name, u_id;
    ELSE
        RAISE NOTICE '⚠️ Developer group not found. Please upgrade diyacrm module first (python3 scripts/upgrade_diyacrm.py)!';
    END IF;
END $$;
"""
    else:
        sql = """
\\pset border 2
\\pset format aligned

\\echo '====================================================================================='
\\echo ' 🏢 DIYA CRM: DEVELOPER USER (UNIT INVENTORY ONLY) SETUP & AUDIT'
\\echo '====================================================================================='

\\echo ''
\\echo '1️⃣ CURRENT DEVELOPER ROLE USERS:'
SELECT 
    u.id AS "User ID",
    u.login AS "Login",
    p.name AS "User Name",
    c.name AS "Default Company",
    u.active AS "Active",
    COALESCE(act.name, 'Visual Unit Matrix') AS "Home Action"
FROM res_users u
JOIN res_partner p ON p.id = u.partner_id
LEFT JOIN res_company c ON c.id = u.company_id
LEFT JOIN ir_act_window act ON act.id = u.action_id
JOIN res_groups_users_rel rel ON rel.uid = u.id
JOIN res_groups g ON g.id = rel.gid
WHERE g.name ILIKE '%developer%' AND g.name ILIKE '%inventory%'
ORDER BY u.id;

\\echo ''
\\echo '2️⃣ ALL ACTIVE USERS & ASSIGNED GROUPS:'
SELECT 
    u.id AS "User ID",
    u.login AS "Login",
    p.name AS "User Name",
    c.name AS "Default Company",
    STRING_AGG(DISTINCT g.name, ', ') AS "Key Roles"
FROM res_users u
JOIN res_partner p ON p.id = u.partner_id
LEFT JOIN res_company c ON c.id = u.company_id
LEFT JOIN res_groups_users_rel rel ON rel.uid = u.id
LEFT JOIN res_groups g ON g.id = rel.gid AND (
    g.name ILIKE '%sales%' OR 
    g.name ILIKE '%crm%' OR 
    g.name ILIKE '%developer%' OR 
    g.name ILIKE '%administrator%'
)
WHERE u.share = FALSE AND u.active = TRUE
GROUP BY u.id, u.login, p.name, c.name
ORDER BY u.id;
"""

    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm"]
    res = subprocess.run(cmd, input=sql, text=True, capture_output=True)
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr)

if __name__ == '__main__':
    run_setup()

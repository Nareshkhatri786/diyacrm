# -*- coding: utf-8 -*-
"""
Diya CRM: Set default Home Action to CRM Pipeline for all non-admin internal users.
"""
import subprocess

def run_set_home_actions():
    print("===================================================================")
    print(" 🚀 Configuring Default Home Action -> CRM Pipeline for Non-Admins")
    print("===================================================================")
    sql = """
DO $$
DECLARE
    crm_action_id INT;
    admin_gid INT;
    upd_count INT := 0;
BEGIN
    -- 1. Find CRM Pipeline window action
    SELECT res_id INTO crm_action_id FROM ir_model_data 
    WHERE module = 'crm' AND name = 'action_your_pipeline' LIMIT 1;

    IF crm_action_id IS NULL THEN
        SELECT id INTO crm_action_id FROM ir_act_window 
        WHERE res_model = 'crm.lead' AND view_mode LIKE '%kanban%' LIMIT 1;
    END IF;

    -- 2. Find Administration / Settings group (base.group_system)
    SELECT res_id INTO admin_gid FROM ir_model_data 
    WHERE module = 'base' AND name = 'group_system' LIMIT 1;

    IF crm_action_id IS NOT NULL AND admin_gid IS NOT NULL THEN
        -- Set Home Action to CRM Pipeline for all non-admin internal users
        UPDATE res_users
        SET action_id = crm_action_id
        WHERE id NOT IN (SELECT uid FROM res_groups_users_rel WHERE gid = admin_gid)
          AND (share = FALSE OR share IS NULL)
          AND id != 1;

        GET DIAGNOSTICS upd_count = ROW_COUNT;
        RAISE NOTICE '✅ Successfully set CRM Pipeline as Home Action for % non-admin user(s)! (Action ID: %)', upd_count, crm_action_id;
    ELSE
        RAISE NOTICE '⚠️ Warning: Could not find crm_action_id (%) or admin_gid (%)', crm_action_id, admin_gid;
    END IF;
END $$;
"""
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)

if __name__ == '__main__':
    run_set_home_actions()

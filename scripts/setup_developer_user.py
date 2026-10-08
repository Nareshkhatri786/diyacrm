# -*- coding: utf-8 -*-
"""
Diya CRM: Helper CLI to configure or create a Developer User (Unit Inventory Only).
Usage:
    python3 scripts/setup_developer_user.py
"""
import sys
import subprocess

def run_setup():
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess, sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DB = "diyacrm"
def psql(title, sql):
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}")
    cmd = ["sudo", "-u", "postgres", "psql", "-d", DB, "-c", sql]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr and "ERROR" in res.stderr:
        print("STDERR:", res.stderr)

PHONE = "9016777628"

psql(f"1. ALL WHATSAPP MESSAGES TO {PHONE}", f"""
SELECT
    m.id,
    to_char(m.date AT TIME ZONE 'Asia/Kolkata', 'DD-Mon-YYYY HH24:MI:SS') AS "Time(IST)",
    m.phone,
    m.direction,
    m.author_name AS sender,
    l.id AS lead_id,
    COALESCE(l.partner_name, l.name, '?') AS lead_name,
    COALESCE(c.name, '?') AS company,
    CASE
        WHEN m.body LIKE '%%Call Follow-up%%' THEN 'AUTO (Dialer Sync)'
        ELSE 'MANUAL (Staff Sent)'
    END AS sent_type,
    LEFT(REPLACE(m.body, E'\\n', ' '), 80) AS body_preview
FROM crm_lead_whatsapp_message m
LEFT JOIN crm_lead l ON l.id = m.lead_id
LEFT JOIN res_company c ON c.id = l.company_id
WHERE m.phone LIKE '%{PHONE}%'
ORDER BY m.date DESC;
""")

psql(f"2. LEAD INFO FOR {PHONE}", f"""
SELECT
    l.id,
    l.name AS lead_name,
    COALESCE(l.partner_name, '?') AS partner_name,
    l.phone,
    l.mobile,
    l.stage_id,
    c.name AS company,
    l.user_id,
    to_char(l.create_date AT TIME ZONE 'Asia/Kolkata', 'DD-Mon-YYYY') AS created,
    to_char(l.last_connected_whatsapp_date AT TIME ZONE 'Asia/Kolkata', 'DD-Mon HH24:MI') AS last_connected_wa,
    to_char(l.last_missed_whatsapp_date AT TIME ZONE 'Asia/Kolkata', 'DD-Mon HH24:MI') AS last_missed_wa
FROM crm_lead l
LEFT JOIN res_company c ON c.id = l.company_id
WHERE l.phone LIKE '%{PHONE}%' OR l.mobile LIKE '%{PHONE}%'
ORDER BY l.create_date DESC;
""")

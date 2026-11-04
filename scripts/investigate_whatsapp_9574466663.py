# -*- coding: utf-8 -*-
"""
Investigate recent WhatsApp messages sent to 9574466663 and all messages sent in the last 2 hours.
"""
import subprocess
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_query(title, sql):
    print("=" * 80)
    print(f" 🔍 {title}")
    print("=" * 80)
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr and "ERROR" in res.stderr:
        print("STDERR:", res.stderr)

# 1. Check messages sent to 9574466663
run_query("1. MESSAGES SENT TO 9574466663 (ALL TIME / RECENT)", """
SELECT 
    m.id,
    (m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19) AS "Time (IST)",
    m.phone,
    m.direction,
    m.author_name,
    l.id AS lead_id,
    l.name AS lead_name,
    c.name AS company_name,
    substring(m.body from 1 for 150) AS body_preview
FROM crm_lead_whatsapp_message m
LEFT JOIN crm_lead l ON l.id = m.lead_id
LEFT JOIN res_company c ON c.id = l.company_id
WHERE m.phone LIKE '%9574466663%'
ORDER BY m.date DESC
LIMIT 10;
""")

# 2. Check chatter mail_message for 9574466663
run_query("2. CHATTER NOTIFICATIONS FOR LEADS WITH 9574466663", """
SELECT 
    mm.id,
    (mm.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19) AS "Time (IST)",
    l.id AS lead_id,
    l.name AS lead_name,
    c.name AS company,
    substring(mm.body from 1 for 200) AS body_preview
FROM mail_message mm
JOIN crm_lead l ON l.id = mm.res_id AND mm.model = 'crm.lead'
JOIN res_company c ON c.id = l.company_id
WHERE l.phone LIKE '%9574466663%'
  AND mm.body ILIKE '%WhatsApp%'
ORDER BY mm.date DESC
LIMIT 5;
""")

# 3. Check ALL WhatsApp messages sent in the last 2 hours (to see if other leads also received messages)
run_query("3. ALL OUTBOUND WHATSAPP MESSAGES IN LAST 3 HOURS", """
SELECT 
    m.id,
    (m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19) AS "Time (IST)",
    m.phone,
    m.author_name,
    l.id AS lead_id,
    l.name AS lead_name,
    c.name AS company,
    substring(m.body from 1 for 120) AS body_preview
FROM crm_lead_whatsapp_message m
LEFT JOIN crm_lead l ON l.id = m.lead_id
LEFT JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
  AND m.date >= NOW() - INTERVAL '3 hours'
ORDER BY m.date DESC
LIMIT 20;
""")

# 4. Check Call Logs / Syncs on 9574466663 in last 24 hours
run_query("4. CALL LOGS / DIALER ACTIVITY ON 9574466663 RECENTLY", """
SELECT 
    l.id AS lead_id,
    l.name,
    l.phone,
    c.name AS company,
    (l.last_call_whatsapp_date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19) AS last_wa_date,
    l.last_call_whatsapp_type,
    (l.write_date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19) AS last_updated_ist
FROM crm_lead l
JOIN res_company c ON c.id = l.company_id
WHERE l.phone LIKE '%9574466663%'
ORDER BY l.write_date DESC
LIMIT 5;
""")

if __name__ == '__main__':
    pass

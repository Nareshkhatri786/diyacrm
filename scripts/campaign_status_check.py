#!/usr/bin/env python3
"""Quick check: campaign process status + crm_lead_whatsapp_message table"""
import subprocess, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def sql(label, q):
    print(f"\n{'='*65}\n {label}\n{'='*65}")
    r = subprocess.run(["sudo","-u","postgres","psql","-d","diyacrm","-c",q], capture_output=True, text=True)
    print(r.stdout)
    if r.stderr and "ERROR" in r.stderr: print("ERR:", r.stderr)

sql("1. crm_lead_whatsapp_message — today's outbound count", """
SELECT
    c.name AS "Company",
    COUNT(*) AS "WA Msgs Today",
    MAX((m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19)) AS "Last Sent (IST)"
FROM crm_lead_whatsapp_message m
JOIN crm_lead l ON l.id = m.lead_id
JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
  AND m.date >= NOW() - INTERVAL '8 hours'
GROUP BY c.name
ORDER BY "WA Msgs Today" DESC;
""")

sql("2. Last 5 outbound WA messages body preview", """
SELECT
    (m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19) AS "Time (IST)",
    c.name AS "Company",
    m.phone AS "Phone",
    substring(m.body FROM 1 FOR 120) AS "Body Preview"
FROM crm_lead_whatsapp_message m
JOIN crm_lead l ON l.id = m.lead_id
JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
  AND m.date >= NOW() - INTERVAL '8 hours'
ORDER BY m.date DESC
LIMIT 5;
""")

sql("3. Campaign chatter (mail_message) — today", """
SELECT COUNT(*) AS "Campaign Chatter Msgs Today"
FROM mail_message
WHERE body ILIKE '%WhatsApp Campaign%'
  AND date >= NOW() - INTERVAL '8 hours';
""")

sql("4. Odoo server log — last WA errors", """
SELECT 1;
""")

# Check campaign process still running
import subprocess as sp
ps = sp.run(["ps","aux"], capture_output=True, text=True)
lines = [l for l in ps.stdout.splitlines() if 'run_stage_campaigns' in l and 'grep' not in l]
print(f"\n{'='*65}")
print(" 5. CAMPAIGN PROCESS STATUS")
print('='*65)
if lines:
    print("✅ Campaign is STILL RUNNING:")
    for l in lines:
        parts = l.split()
        print(f"   PID: {parts[1]} | CPU: {parts[2]}% | MEM: {parts[3]}% | User: {parts[0]}")
else:
    print("⚠️  Campaign process is NOT running (completed or crashed)")
    # Check exit
    print("\nChecking nohup log tail:")
    try:
        tail = sp.run(["tail","-20","/opt/odoo19/custom_addons/diyacrm/campaign_run.log"], capture_output=True, text=True)
        print(tail.stdout)
    except: pass

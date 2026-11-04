#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto vs Manual WhatsApp Analysis - Last 10 Days
Auto = Call Follow-up (body starts with 📲)
Manual = Staff ne wizard/button se bheja (baaki sab)
"""
import subprocess, sys
from datetime import datetime, timedelta, timezone

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

now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
since_10d = (now_ist - timedelta(days=10)).astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
print(f"\n📅 Period: {(now_ist - timedelta(days=10)).strftime('%d %b %Y')} to {now_ist.strftime('%d %b %Y %H:%M IST')}")
print(f"\n📌 Auto  = Dialer sync se gaya (body me '📲 Call Follow-up')")
print(f"📌 Manual = Staff ne khud bheja (CRM wizard/button se)")

# 1. Overall Auto vs Manual
psql("1. OVERALL AUTO vs MANUAL SPLIT", f"""
SELECT
    CASE
        WHEN m.body LIKE '📲 Call Follow-up%%' OR m.body LIKE '%Call Follow-up%'
        THEN 'AUTO (Dialer Sync)'
        ELSE 'MANUAL (Staff Sent)'
    END AS sent_type,
    COUNT(*)                     AS total_messages,
    COUNT(DISTINCT m.phone)      AS unique_clients,
    COUNT(DISTINCT m.author_name) AS unique_senders
FROM crm_lead_whatsapp_message m
WHERE m.direction = 'outbound'
  AND m.date >= '{since_10d}'
GROUP BY sent_type
ORDER BY total_messages DESC;
""")

# 2. Per staff - Auto vs Manual
psql("2. STAFF-WISE: Auto vs Manual Breakdown", f"""
SELECT
    COALESCE(m.author_name, 'Unknown') AS sender,
    COUNT(*) FILTER (WHERE m.body LIKE '%%Call Follow-up%%') AS auto_messages,
    COUNT(*) FILTER (WHERE m.body NOT LIKE '%%Call Follow-up%%') AS manual_messages,
    COUNT(*) AS total,
    ROUND(
        COUNT(*) FILTER (WHERE m.body LIKE '%%Call Follow-up%%') * 100.0 / COUNT(*), 1
    ) AS auto_pct
FROM crm_lead_whatsapp_message m
WHERE m.direction = 'outbound'
  AND m.date >= '{since_10d}'
GROUP BY m.author_name
ORDER BY total DESC;
""")

# 3. Day-wise Auto vs Manual
psql("3. DAY-WISE: Auto vs Manual", f"""
SELECT
    to_char(m.date AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD (Dy)') AS date_ist,
    COUNT(*) FILTER (WHERE m.body LIKE '%%Call Follow-up%%') AS auto_msgs,
    COUNT(*) FILTER (WHERE m.body NOT LIKE '%%Call Follow-up%%') AS manual_msgs,
    COUNT(*) AS total
FROM crm_lead_whatsapp_message m
WHERE m.direction = 'outbound'
  AND m.date >= '{since_10d}'
GROUP BY 1
ORDER BY 1 DESC;
""")

# 4. Company-wise Auto vs Manual
psql("4. COMPANY-WISE: Auto vs Manual", f"""
SELECT
    COALESCE(c.name, 'Unknown') AS company,
    COUNT(*) FILTER (WHERE m.body LIKE '%%Call Follow-up%%') AS auto_msgs,
    COUNT(*) FILTER (WHERE m.body NOT LIKE '%%Call Follow-up%%') AS manual_msgs,
    COUNT(*) AS total
FROM crm_lead_whatsapp_message m
LEFT JOIN crm_lead l ON l.id = m.lead_id
LEFT JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
  AND m.date >= '{since_10d}'
GROUP BY c.name
ORDER BY total DESC;
""")

# 5. Manual messages detail - what did staff manually send?
psql("5. MANUAL MESSAGES - What Staff Sent (Template Types)", f"""
SELECT
    COALESCE(m.author_name, 'Unknown') AS sender,
    LEFT(m.body, 60) AS message_start,
    COUNT(*) AS times_sent
FROM crm_lead_whatsapp_message m
WHERE m.direction = 'outbound'
  AND m.date >= '{since_10d}'
  AND m.body NOT LIKE '%%Call Follow-up%%'
GROUP BY m.author_name, LEFT(m.body, 60)
ORDER BY times_sent DESC
LIMIT 20;
""")

# 6. Days with ZERO manual messages (only auto happened)
psql("6. STAFF MANUAL ACTIVITY per DAY (0 manual = no real effort that day)", f"""
SELECT
    to_char(m.date AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD (Dy)') AS date_ist,
    COALESCE(m.author_name, 'Unknown') AS sender,
    COUNT(*) FILTER (WHERE m.body NOT LIKE '%%Call Follow-up%%') AS manual_msgs,
    COUNT(*) FILTER (WHERE m.body LIKE '%%Call Follow-up%%') AS auto_msgs
FROM crm_lead_whatsapp_message m
WHERE m.direction = 'outbound'
  AND m.date >= '{since_10d}'
GROUP BY 1, m.author_name
ORDER BY 1 DESC, manual_msgs DESC;
""")

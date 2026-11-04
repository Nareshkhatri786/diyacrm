#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync-Call Auto WhatsApp - Last 10 Days Analysis
crm_lead_whatsapp_message table me outbound messages check karo
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
print(f"\n📅 Checking from: {(now_ist - timedelta(days=10)).strftime('%d %b %Y %H:%M IST')} to NOW")

# 1. Grand total
psql("1. GRAND TOTAL (Last 10 Days)", f"""
SELECT
    COUNT(*)                          AS total_messages,
    COUNT(DISTINCT m.phone)           AS unique_clients,
    COUNT(DISTINCT m.lead_id)         AS unique_leads,
    COUNT(DISTINCT m.author_name)     AS unique_senders
FROM crm_lead_whatsapp_message m
WHERE m.direction = 'outbound'
  AND m.date >= '{since_10d}';
""")

# 2. Day-wise breakdown
psql("2. DAY-WISE BREAKDOWN", f"""
SELECT
    to_char(m.date AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD (Dy)') AS date_ist,
    COUNT(*)                     AS messages,
    COUNT(DISTINCT m.phone)      AS unique_clients
FROM crm_lead_whatsapp_message m
WHERE m.direction = 'outbound'
  AND m.date >= '{since_10d}'
GROUP BY 1
ORDER BY 1 DESC;
""")

# 3. Company-wise total
psql("3. COMPANY-WISE TOTAL", f"""
SELECT
    COALESCE(c.name, 'Unknown')   AS company,
    COUNT(*)                      AS messages,
    COUNT(DISTINCT m.phone)       AS unique_clients
FROM crm_lead_whatsapp_message m
LEFT JOIN crm_lead l ON l.id = m.lead_id
LEFT JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
  AND m.date >= '{since_10d}'
GROUP BY c.name
ORDER BY messages DESC;
""")

# 4. Sender-wise total
psql("4. SENDER (STAFF) WISE TOTAL", f"""
SELECT
    COALESCE(m.author_name, 'Unknown/System') AS sender,
    COUNT(*)                                   AS messages,
    COUNT(DISTINCT m.phone)                    AS unique_clients,
    COUNT(DISTINCT m.lead_id)                  AS unique_leads
FROM crm_lead_whatsapp_message m
WHERE m.direction = 'outbound'
  AND m.date >= '{since_10d}'
GROUP BY m.author_name
ORDER BY messages DESC;
""")

# 5. Clients who got 2+ messages in 1 hour (double-blast detection)
psql("5. DOUBLE-BLAST DETECTION (Same client, 2+ msgs within 60 min)", f"""
SELECT
    m.phone,
    COALESCE(l.partner_name, l.name, '?') AS lead_name,
    COALESCE(c.name, '?')                 AS company,
    COUNT(*)                              AS msg_count,
    to_char(MIN(m.date) AT TIME ZONE 'Asia/Kolkata', 'DD-Mon HH24:MI') AS first_msg,
    to_char(MAX(m.date) AT TIME ZONE 'Asia/Kolkata', 'DD-Mon HH24:MI') AS last_msg
FROM crm_lead_whatsapp_message m
LEFT JOIN crm_lead l ON l.id = m.lead_id
LEFT JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
  AND m.date >= '{since_10d}'
GROUP BY m.phone, l.partner_name, l.name, c.name
HAVING COUNT(*) >= 2
ORDER BY msg_count DESC
LIMIT 30;
""")

# 6. Burst sessions (10+ msgs in 1 minute = dialer batch sync)
psql("6. DIALER BATCH SYNC SESSIONS (10+ msgs in same minute)", f"""
SELECT
    to_char(m.date AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI') AS minute_ist,
    COUNT(*)                     AS messages,
    COUNT(DISTINCT m.author_name) AS senders,
    STRING_AGG(DISTINCT m.author_name, ', ') AS sender_names
FROM crm_lead_whatsapp_message m
WHERE m.direction = 'outbound'
  AND m.date >= '{since_10d}'
GROUP BY 1
HAVING COUNT(*) >= 5
ORDER BY 1 DESC;
""")

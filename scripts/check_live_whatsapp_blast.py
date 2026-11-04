#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live WhatsApp Blast Monitor - Last 20 minutes
Direct psql approach (no Odoo import needed)
"""
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DB = "diyacrm"

def psql(sql):
    cmd = ["sudo", "-u", "postgres", "psql", "-d", DB, "-c", sql]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout, res.stderr

now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
since_ist = now_ist - timedelta(minutes=20)
# Format for SQL
since_str = since_ist.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

print(f"\n{'='*80}")
print(f" 📡 LIVE WhatsApp Blast Monitor")
print(f" Period: {since_ist.strftime('%H:%M:%S IST')}  →  {now_ist.strftime('%H:%M:%S IST')}")
print(f"{'='*80}")

# ── 1. Total count + per-minute burst ───────────────────────────────────────
sql_summary = f"""
SELECT
    to_char(m.date AT TIME ZONE 'Asia/Kolkata', 'HH24:MI') AS minute_ist,
    COUNT(*) AS msg_count
FROM mail_message m
WHERE m.message_type = 'whatsapp'
  AND m.date >= '{since_str}'
  AND m.phone_number IS NOT NULL
GROUP BY 1
ORDER BY 1 DESC;
"""
out, err = psql(sql_summary)
print("\n⚡ BURST DETECTION (messages per minute):")
print(out)

# ── 2. Company-wise breakdown ────────────────────────────────────────────────
sql_company = f"""
SELECT
    COALESCE(c.name, 'Unknown') AS company,
    COUNT(*) AS messages,
    COUNT(DISTINCT m.phone_number) AS unique_phones
FROM mail_message m
LEFT JOIN crm_lead l ON l.id = m.res_id AND m.model = 'crm.lead'
LEFT JOIN res_company c ON c.id = l.company_id
WHERE m.message_type = 'whatsapp'
  AND m.date >= '{since_str}'
  AND m.phone_number IS NOT NULL
GROUP BY c.name
ORDER BY messages DESC;
"""
out, err = psql(sql_company)
print("📊 COMPANY-WISE BREAKDOWN:")
print(out)

# ── 3. Sender-wise breakdown ─────────────────────────────────────────────────
sql_sender = f"""
SELECT
    COALESCE(p.name, 'System/Unknown') AS sender,
    COUNT(*) AS messages
FROM mail_message m
LEFT JOIN res_partner p ON p.id = m.author_id
WHERE m.message_type = 'whatsapp'
  AND m.date >= '{since_str}'
  AND m.phone_number IS NOT NULL
GROUP BY p.name
ORDER BY messages DESC;
"""
out, err = psql(sql_sender)
print("👤 SENDER-WISE BREAKDOWN:")
print(out)

# ── 4. Full detail log ───────────────────────────────────────────────────────
sql_detail = f"""
SELECT
    to_char(m.date AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS "Time(IST)",
    m.id AS msg_id,
    l.id AS lead_id,
    LEFT(COALESCE(l.partner_name, '?'), 20) AS lead_name,
    m.phone_number AS phone,
    LEFT(COALESCE(c.name, '?'), 18) AS company,
    LEFT(COALESCE(p.name, '?'), 16) AS sender,
    LEFT(REPLACE(m.body, E'\\n', ' '), 50) AS body_preview
FROM mail_message m
LEFT JOIN res_partner p ON p.id = m.author_id
LEFT JOIN crm_lead l ON l.id = m.res_id AND m.model = 'crm.lead'
LEFT JOIN res_company c ON c.id = l.company_id
WHERE m.message_type = 'whatsapp'
  AND m.date >= '{since_str}'
  AND m.phone_number IS NOT NULL
ORDER BY m.date DESC
LIMIT 200;
"""
out, err = psql(sql_detail)
print("📋 DETAILED MESSAGE LOG (Most Recent First):")
print(out)

if err and "ERROR" in err:
    print("STDERR:", err)


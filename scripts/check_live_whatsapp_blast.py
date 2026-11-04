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
since_str = since_ist.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

print(f"\n{'='*80}")
print(f" 📡 LIVE WhatsApp Blast Monitor")
print(f" Period: {since_ist.strftime('%H:%M:%S IST')}  →  {now_ist.strftime('%H:%M:%S IST')}")
print(f"{'='*80}")

# ── 1. Total count ───────────────────────────────────────────────────────────
sql_total = f"""
SELECT COUNT(*) AS total_messages_sent
FROM crm_lead_whatsapp_message m
WHERE m.direction = 'outbound'
  AND m.date >= '{since_str}';
"""
out, err = psql(sql_total)
print("\n📊 TOTAL MESSAGES SENT (Last 20 min):")
print(out)
if err and "ERROR" in err:
    print("STDERR:", err)

# ── 2. Per-minute burst detection ────────────────────────────────────────────
sql_burst = f"""
SELECT
    to_char(m.date AT TIME ZONE 'Asia/Kolkata', 'HH24:MI') AS minute_ist,
    COUNT(*) AS msg_count
FROM crm_lead_whatsapp_message m
WHERE m.direction = 'outbound'
  AND m.date >= '{since_str}'
GROUP BY 1
ORDER BY 1 DESC;
"""
out, err = psql(sql_burst)
print("⚡ BURST DETECTION (messages per minute):")
print(out)
if err and "ERROR" in err:
    print("STDERR:", err)

# ── 3. Company-wise breakdown ─────────────────────────────────────────────────
sql_company = f"""
SELECT
    COALESCE(c.name, 'Unknown') AS company,
    COUNT(*) AS messages,
    COUNT(DISTINCT m.phone) AS unique_phones
FROM crm_lead_whatsapp_message m
LEFT JOIN crm_lead l ON l.id = m.lead_id
LEFT JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
  AND m.date >= '{since_str}'
GROUP BY c.name
ORDER BY messages DESC;
"""
out, err = psql(sql_company)
print("🏢 COMPANY-WISE BREAKDOWN:")
print(out)
if err and "ERROR" in err:
    print("STDERR:", err)

# ── 4. Sender-wise breakdown ──────────────────────────────────────────────────
sql_sender = f"""
SELECT
    COALESCE(m.author_name, 'System/Unknown') AS sender,
    COUNT(*) AS messages
FROM crm_lead_whatsapp_message m
WHERE m.direction = 'outbound'
  AND m.date >= '{since_str}'
GROUP BY m.author_name
ORDER BY messages DESC;
"""
out, err = psql(sql_sender)
print("👤 SENDER-WISE BREAKDOWN:")
print(out)
if err and "ERROR" in err:
    print("STDERR:", err)

# ── 5. Full detail log ────────────────────────────────────────────────────────
sql_detail = f"""
SELECT
    to_char(m.date AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS "Time(IST)",
    m.id AS msg_id,
    m.lead_id,
    LEFT(COALESCE(l.partner_name, l.name, '?'), 20) AS lead_name,
    m.phone,
    LEFT(COALESCE(c.name, '?'), 18) AS company,
    LEFT(COALESCE(m.author_name, '?'), 16) AS sender,
    LEFT(REPLACE(m.body, E'\\n', ' '), 55) AS body_preview
FROM crm_lead_whatsapp_message m
LEFT JOIN crm_lead l ON l.id = m.lead_id
LEFT JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
  AND m.date >= '{since_str}'
ORDER BY m.date DESC
LIMIT 200;
"""
out, err = psql(sql_detail)
print("📋 DETAILED MESSAGE LOG (Most Recent First):")
print(out)
if err and "ERROR" in err:
    print("STDERR:", err)


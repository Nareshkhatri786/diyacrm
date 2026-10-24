#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diya CRM: Quick check — why are campaign WhatsApp messages failing?
Reads last 50 failed campaign chatter entries from PostgreSQL and prints the Meta API error.
Usage:
  python3 scripts/check_campaign_failure_reason.py
"""
import subprocess
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SQL = r"""
\pset border 2
\pset format aligned

\echo '=================================================================='
\echo ' 🔍 DIYA CRM: CAMPAIGN WHATSAPP FAILURE REASON CHECKER'
\echo '=================================================================='

\echo ''
\echo '1. LAST 30 CAMPAIGN FAILURES (with Meta error text):'
SELECT
    l.name AS "Lead",
    c.name AS "Company",
    substring(mm.body FROM 1 FOR 220) AS "Error Preview",
    (mm.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19) AS "Time (IST)"
FROM mail_message mm
JOIN crm_lead l ON l.id = mm.res_id AND mm.model = 'crm.lead'
JOIN res_company c ON c.id = l.company_id
WHERE mm.body ILIKE '%WhatsApp Campaign Failed%'
ORDER BY mm.date DESC
LIMIT 30;

\echo ''
\echo '2. CAMPAIGN FAILURE COUNT BY COMPANY:'
SELECT
    c.name AS "Company",
    COUNT(*) AS "Total Failures"
FROM mail_message mm
JOIN crm_lead l ON l.id = mm.res_id AND mm.model = 'crm.lead'
JOIN res_company c ON c.id = l.company_id
WHERE mm.body ILIKE '%WhatsApp Campaign Failed%'
  AND mm.date >= NOW() - INTERVAL '24 hours'
GROUP BY c.name
ORDER BY "Total Failures" DESC;

\echo ''
\echo '3. CAMPAIGN SUCCESS COUNT BY COMPANY (Today):'
SELECT
    c.name AS "Company",
    COUNT(*) AS "Total Delivered ✅"
FROM mail_message mm
JOIN crm_lead l ON l.id = mm.res_id AND mm.model = 'crm.lead'
JOIN res_company c ON c.id = l.company_id
WHERE mm.body ILIKE '%WhatsApp Campaign Delivered%'
  AND mm.date >= NOW() - INTERVAL '24 hours'
GROUP BY c.name
ORDER BY "Total Delivered ✅" DESC;

\echo ''
\echo '4. STAGE-WISE CAMPAIGN DELIVERY (Today):'
SELECT
    c.name AS "Company",
    CASE
        WHEN mm.body ILIKE '%Stage 1%' OR mm.body ILIKE '%New Lead%' THEN 'Stage 1: New Lead'
        WHEN mm.body ILIKE '%Stage 2%' OR mm.body ILIKE '%Contacted%' THEN 'Stage 2: Contacted'
        WHEN mm.body ILIKE '%Stage 4%' OR mm.body ILIKE '%Scheduled%' THEN 'Stage 4: Site Visit Scheduled'
        WHEN mm.body ILIKE '%Stage 5%' OR mm.body ILIKE '%Visit Done%' THEN 'Stage 5: Site Visit Done'
        WHEN mm.body ILIKE '%Stage 6%' OR mm.body ILIKE '%Negotiation%' THEN 'Stage 6: Negotiation'
        ELSE 'Other'
    END AS "Stage",
    COUNT(*) AS "Delivered ✅"
FROM mail_message mm
JOIN crm_lead l ON l.id = mm.res_id AND mm.model = 'crm.lead'
JOIN res_company c ON c.id = l.company_id
WHERE mm.body ILIKE '%WhatsApp Campaign Delivered%'
  AND mm.date >= NOW() - INTERVAL '24 hours'
GROUP BY c.name, "Stage"
ORDER BY c.name, "Stage";
"""

def main():
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", SQL]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr and "ERROR" in res.stderr:
        print("STDERR:", res.stderr)

if __name__ == '__main__':
    main()

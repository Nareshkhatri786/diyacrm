#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diya CRM: Campaign failure reason checker + stage-wise delivery report.
Usage:
  python3 scripts/check_campaign_failure_reason.py
"""
import subprocess
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_sql(label, sql):
    print(f"\n{'='*70}")
    print(f" {label}")
    print('='*70)
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout)
    if res.stderr and "ERROR" in res.stderr:
        print("ERROR:", res.stderr)

# 1. Why are messages failing? — Last 10 unique Meta errors
run_sql("1. META API FAILURE REASONS (Last 10 unique errors)", """
SELECT DISTINCT
    substring(mm.body FROM position('Error' IN mm.body) FOR 200) AS "Meta Error Reason",
    COUNT(*) AS "Occurrences"
FROM mail_message mm
WHERE mm.body ILIKE '%WhatsApp Campaign Failed%'
  AND mm.date >= NOW() - INTERVAL '24 hours'
GROUP BY "Meta Error Reason"
ORDER BY "Occurrences" DESC
LIMIT 10;
""")

# 2. Company-wise fail vs success
run_sql("2. COMPANY-WISE CAMPAIGN RESULT (Today)", """
SELECT
    c.name AS "Company",
    COUNT(CASE WHEN mm.body ILIKE '%Campaign Delivered%' THEN 1 END) AS "Delivered ✅",
    COUNT(CASE WHEN mm.body ILIKE '%Campaign Failed%'   THEN 1 END) AS "Failed ❌"
FROM mail_message mm
JOIN crm_lead l ON l.id = mm.res_id AND mm.model = 'crm.lead'
JOIN res_company c ON c.id = l.company_id
WHERE mm.body ILIKE '%WhatsApp Campaign%'
  AND mm.date >= NOW() - INTERVAL '24 hours'
GROUP BY c.name
ORDER BY "Delivered ✅" DESC;
""")

# 3. Stage-wise delivery breakdown
run_sql("3. STAGE-WISE DELIVERY BREAKDOWN (Today)", """
SELECT
    c.name AS "Company",
    CASE
        WHEN mm.body ILIKE '%Stage 1%' OR mm.body ILIKE '%New Lead%'         THEN 'Stage 1: New Lead'
        WHEN mm.body ILIKE '%Stage 2%' OR mm.body ILIKE '%Contacted%'        THEN 'Stage 2: Contacted'
        WHEN mm.body ILIKE '%Stage 4%' OR mm.body ILIKE '%Scheduled%'        THEN 'Stage 4: Site Visit Scheduled'
        WHEN mm.body ILIKE '%Stage 5%' OR mm.body ILIKE '%Visit Done%'       THEN 'Stage 5: Site Visit Done'
        WHEN mm.body ILIKE '%Stage 6%' OR mm.body ILIKE '%Negotiation%'      THEN 'Stage 6: Negotiation'
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
""")

# 4. Overall summary
run_sql("4. OVERALL SUMMARY (Today)", """
SELECT
    COUNT(CASE WHEN mm.body ILIKE '%Campaign Delivered%' THEN 1 END) AS "Total Delivered ✅",
    COUNT(CASE WHEN mm.body ILIKE '%Campaign Failed%'   THEN 1 END) AS "Total Failed ❌",
    MAX((mm.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19)) AS "Last Activity (IST)"
FROM mail_message mm
WHERE mm.body ILIKE '%WhatsApp Campaign%'
  AND mm.date >= NOW() - INTERVAL '24 hours';
""")

if __name__ == '__main__':
    pass

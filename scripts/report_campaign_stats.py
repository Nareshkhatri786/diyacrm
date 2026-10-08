# -*- coding: utf-8 -*-
"""
Diya CRM: Comprehensive Campaign & WhatsApp Statistics Report.
Usage:
    python3 scripts/report_campaign_stats.py
"""
import subprocess

def run_stats():
    sql = """
\\pset border 2
\\pset format aligned

\\echo '====================================================================================='
\\echo ' 📊 DIYA CRM: WHATSAPP & CAMPAIGN AUDIT REPORT'
\\echo '====================================================================================='

\\echo ''
\\echo '1️⃣ REGISTERED COMPANIES IN SYSTEM:'
SELECT id, name FROM res_company ORDER BY id;

\\echo ''
\\echo '2️⃣ ALL OUTBOUND WHATSAPP MESSAGES BY COMPANY (crm_lead_whatsapp_message):'
SELECT 
    c.name AS "Company",
    COUNT(m.id) AS "Total Outbound WA",
    COUNT(DISTINCT m.lead_id) AS "Unique Leads",
    COUNT(CASE WHEN m.body ILIKE '%campaign%' OR m.body ILIKE '%re-engagement%' THEN 1 END) AS "Stage Campaigns",
    COUNT(CASE WHEN m.body ILIKE '%site visit%' OR m.body ILIKE '%sample house%' THEN 1 END) AS "Visit / Sample House",
    MIN((m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19)) AS "First Sent (IST)",
    MAX((m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19)) AS "Latest Sent (IST)"
FROM crm_lead_whatsapp_message m
JOIN crm_lead l ON l.id = m.lead_id
JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
GROUP BY c.name
ORDER BY c.name;

\\echo ''
\\echo '3️⃣ WHATSAPP CAMPAIGN LOGS IN CHATTER (mail_message):'
SELECT 
    c.name AS "Company",
    COUNT(CASE WHEN mm.body ILIKE '%WhatsApp Campaign Delivered%' THEN 1 END) AS "Delivered ✅",
    COUNT(CASE WHEN mm.body ILIKE '%WhatsApp Campaign Failed%' THEN 1 END) AS "Failed ❌",
    COUNT(CASE WHEN mm.body ILIKE '%WhatsApp%' AND mm.body NOT ILIKE '%Campaign%' THEN 1 END) AS "Other WA Messages"
FROM mail_message mm
JOIN crm_lead l ON l.id = mm.res_id AND mm.model = 'crm.lead'
JOIN res_company c ON c.id = l.company_id
WHERE mm.body ILIKE '%WhatsApp%'
GROUP BY c.name
ORDER BY c.name;

\\echo ''
\\echo '4️⃣ LEADS WITH WHATSAPP TIMESTAMP ON RECORD (crm_lead):'
SELECT 
    c.name AS "Company",
    COUNT(l.id) AS "Total Leads",
    COUNT(CASE WHEN l.last_call_whatsapp_date IS NOT NULL THEN 1 END) AS "Has WA Sent Date",
    COUNT(CASE WHEN l.last_call_whatsapp_type = 'campaign' THEN 1 END) AS "Type = Campaign",
    COUNT(CASE WHEN l.last_call_whatsapp_type = 'answered' THEN 1 END) AS "Type = Answered",
    COUNT(CASE WHEN l.last_call_whatsapp_type = 'no_answer' THEN 1 END) AS "Type = No Answer",
    MAX((l.last_call_whatsapp_date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19)) AS "Latest WA (IST)"
FROM crm_lead l
JOIN res_company c ON c.id = l.company_id
GROUP BY c.name
ORDER BY c.name;

\\echo ''
\\echo '5️⃣ RECENT OUTBOUND MESSAGES ACROSS ALL COMPANIES (Latest 15):'
SELECT 
    c.name AS "Company",
    SUBSTRING(l.name FROM 1 FOR 22) AS "Lead Name",
    m.phone AS "Phone",
    (m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19) AS "Sent At (IST)",
    m.author_name AS "Sent By",
    SUBSTRING(m.body FROM 1 FOR 45) AS "Body Preview"
FROM crm_lead_whatsapp_message m
JOIN crm_lead l ON l.id = m.lead_id
JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
ORDER BY m.date DESC
LIMIT 15;
"""

    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm"]
    res = subprocess.run(cmd, input=sql, text=True, capture_output=True)
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr)

if __name__ == '__main__':
    run_stats()

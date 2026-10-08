# -*- coding: utf-8 -*-
"""
Diya CRM: Campaign WhatsApp Stats Reporter for Shreemad Family & The 1st Residency.
Usage:
    python3 scripts/report_campaign_stats.py
"""
import sys
import subprocess

def run_stats():
    sql = """
\\pset border 2
\\pset format aligned

\\echo '====================================================================================='
\\echo ' 📊 DIYA CRM: CAMPAIGN WHATSAPP SENT REPORT (Shreemad & The 1st Residency)'
\\echo '====================================================================================='

\\echo ''
\\echo '1️⃣ SUMMARY BY PROJECT (Total Sent & Unique Leads):'
SELECT 
    c.name AS "Project / Company",
    COUNT(m.id) AS "Total WhatsApp Sent",
    COUNT(DISTINCT m.lead_id) AS "Unique Leads",
    MIN((m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19)) AS "First Sent (IST)",
    MAX((m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19)) AS "Latest Sent (IST)"
FROM crm_lead_whatsapp_message m
JOIN crm_lead l ON l.id = m.lead_id
JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
  AND (m.body ILIKE '%campaign%' OR m.body ILIKE '%re-engagement%')
  AND (c.name ILIKE '%shreemad%' OR c.name ILIKE '%1st%' OR c.name ILIKE '%first%' OR c.name ILIKE '%radhe%')
GROUP BY c.name
ORDER BY c.name;

\\echo ''
\\echo '2️⃣ DELIVERY STATUS IN CHATTER (Delivered vs Failed via Meta Cloud API):'
SELECT 
    c.name AS "Project / Company",
    COUNT(CASE WHEN mm.body ILIKE '%WhatsApp Campaign Delivered%' THEN 1 END) AS "Delivered ✅",
    COUNT(CASE WHEN mm.body ILIKE '%WhatsApp Campaign Failed%' THEN 1 END) AS "Failed ❌"
FROM mail_message mm
JOIN crm_lead l ON l.id = mm.res_id AND mm.model = 'crm.lead'
JOIN res_company c ON c.id = l.company_id
WHERE (mm.body ILIKE '%WhatsApp Campaign Delivered%' OR mm.body ILIKE '%WhatsApp Campaign Failed%')
  AND (c.name ILIKE '%shreemad%' OR c.name ILIKE '%1st%' OR c.name ILIKE '%first%' OR c.name ILIKE '%radhe%')
GROUP BY c.name
ORDER BY c.name;

\\echo ''
\\echo '3️⃣ BREAKDOWN BY CRM STAGE:'
SELECT 
    c.name AS "Project / Company",
    COALESCE(s.name::jsonb->>'en_US', s.name::text) AS "Stage Name",
    COUNT(m.id) AS "Messages Sent"
FROM crm_lead_whatsapp_message m
JOIN crm_lead l ON l.id = m.lead_id
JOIN res_company c ON c.id = l.company_id
LEFT JOIN crm_stage s ON s.id = l.stage_id
WHERE m.direction = 'outbound'
  AND (m.body ILIKE '%campaign%' OR m.body ILIKE '%re-engagement%')
  AND (c.name ILIKE '%shreemad%' OR c.name ILIKE '%1st%' OR c.name ILIKE '%first%' OR c.name ILIKE '%radhe%')
GROUP BY c.name, COALESCE(s.name::jsonb->>'en_US', s.name::text)
ORDER BY c.name, "Messages Sent" DESC;

\\echo ''
\\echo '4️⃣ BREAKDOWN BY DATE (IST):'
SELECT 
    c.name AS "Project / Company",
    (m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::date AS "Date (IST)",
    COUNT(m.id) AS "Messages Sent"
FROM crm_lead_whatsapp_message m
JOIN crm_lead l ON l.id = m.lead_id
JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
  AND (m.body ILIKE '%campaign%' OR m.body ILIKE '%re-engagement%')
  AND (c.name ILIKE '%shreemad%' OR c.name ILIKE '%1st%' OR c.name ILIKE '%first%' OR c.name ILIKE '%radhe%')
GROUP BY c.name, (m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::date
ORDER BY "Date (IST)" DESC, c.name;

\\echo ''
\\echo '5️⃣ RECENT 10 CAMPAIGN DELIVERIES (Sample):'
SELECT 
    c.name AS "Project",
    SUBSTRING(l.name FROM 1 FOR 25) AS "Lead Name",
    m.phone AS "Phone",
    (m.date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')::varchar(19) AS "Sent At (IST)",
    COALESCE(s.name::jsonb->>'en_US', s.name::text) AS "Stage",
    m.author_name AS "Sent By"
FROM crm_lead_whatsapp_message m
JOIN crm_lead l ON l.id = m.lead_id
JOIN res_company c ON c.id = l.company_id
LEFT JOIN crm_stage s ON s.id = l.stage_id
WHERE m.direction = 'outbound'
  AND (m.body ILIKE '%campaign%' OR m.body ILIKE '%re-engagement%')
  AND (c.name ILIKE '%shreemad%' OR c.name ILIKE '%1st%' OR c.name ILIKE '%first%' OR c.name ILIKE '%radhe%')
ORDER BY m.date DESC
LIMIT 10;
"""

    commands = [
        ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql],
        ["psql", "-d", "diyacrm", "-c", sql],
        ["psql", "-U", "odoo19", "-d", "diyacrm", "-c", sql],
    ]

    for cmd in commands:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                print(res.stdout)
                return
        except Exception:
            pass

    # Fallback to psycopg2
    try:
        import psycopg2
        conn = psycopg2.connect(dbname="diyacrm")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.name AS company,
                    COUNT(m.id) AS total_sent,
                    COUNT(DISTINCT m.lead_id) AS unique_leads
                FROM crm_lead_whatsapp_message m
                JOIN crm_lead l ON l.id = m.lead_id
                JOIN res_company c ON c.id = l.company_id
                WHERE m.direction = 'outbound'
                  AND (m.body ILIKE '%campaign%' OR m.body ILIKE '%re-engagement%')
                  AND (c.name ILIKE '%shreemad%' OR c.name ILIKE '%1st%' OR c.name ILIKE '%first%' OR c.name ILIKE '%radhe%')
                GROUP BY c.name;
            """)
            rows = cur.fetchall()
            print("\nProject Summary:")
            for r in rows:
                print(f"• {r[0]}: {r[1]} messages sent ({r[2]} unique leads)")
        conn.close()
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == '__main__':
    run_stats()

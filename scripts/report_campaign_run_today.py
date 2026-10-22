# -*- coding: utf-8 -*-
"""
Diya CRM: Real-Time Campaign Execution Report (Today / Recent)
Inspects outbound WhatsApp messages and chatter logs for campaigns run today.
"""
import sys
import os
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SQL_REPORT = """
DO $$
DECLARE
    r RECORD;
    v_total_today INT;
    v_delivered INT;
    v_failed INT;
BEGIN
    RAISE NOTICE '==================================================================';
    RAISE NOTICE ' 🚀 DIYA CRM: WHATSAPP CAMPAIGN RUN AUDIT REPORT (TODAY)';
    RAISE NOTICE '==================================================================';

    -- 1. Campaign Deliveries from mail_message in the last 24 hours
    SELECT count(*) INTO v_delivered
    FROM mail_message
    WHERE model = 'crm.lead'
      AND (body ILIKE '%Campaign Delivered%' OR body ILIKE '%WhatsApp Delivered%')
      AND date >= NOW() - INTERVAL '24 hours';

    SELECT count(*) INTO v_failed
    FROM mail_message
    WHERE model = 'crm.lead'
      AND (body ILIKE '%Campaign Failed%' OR body ILIKE '%WhatsApp Failed%')
      AND date >= NOW() - INTERVAL '24 hours';

    RAISE NOTICE '1. LAST 24 HOURS ACTIVITY SUMMARY:';
    RAISE NOTICE '   • Total Delivered Successfully: %', v_delivered;
    RAISE NOTICE '   • Total Failed / Rejected:      %', v_failed;
    RAISE NOTICE '';

    -- 2. Project & Campaign Type Breakdown (Last 24 Hours)
    RAISE NOTICE '2. BREAKDOWN BY PROJECT & MESSAGE TYPE (LAST 24 HOURS):';
    RAISE NOTICE '%-25s | %-30s | %-10s | %-19s | %-19s',
                 'Project', 'Message / Campaign Type', 'Count', 'First Sent', 'Last Sent';
    RAISE NOTICE '-------------------------------------------------------------------------------------------------------------';

    FOR r IN (
        SELECT 
            c.name AS project,
            CASE 
                WHEN m.body LIKE '🚀 WhatsApp Campaign%' THEN SUBSTRING(m.body FROM 1 FOR 35)
                WHEN m.body LIKE '📲 Call Follow-up%' THEN SUBSTRING(m.body FROM 1 FOR 35)
                WHEN m.body LIKE '%Site Visit%' THEN 'Site Visit WhatsApp'
                ELSE 'Outbound WhatsApp'
            END AS msg_type,
            count(*) AS total_count,
            min(m.date) AS first_date,
            max(m.date) AS last_date
        FROM crm_lead_whatsapp_message m
        JOIN crm_lead l ON l.id = m.lead_id
        JOIN res_company c ON c.id = l.company_id
        WHERE m.direction = 'outbound'
          AND m.date >= NOW() - INTERVAL '24 hours'
        GROUP BY c.name, msg_type
        ORDER BY max(m.date) DESC
    ) LOOP
        RAISE NOTICE '%-25s | %-30s | %-10s | %-19s | %-19s',
                     r.project, r.msg_type, r.total_count, r.first_date::text, r.last_date::text;
    END LOOP;

    RAISE NOTICE '-------------------------------------------------------------------------------------------------------------';
    RAISE NOTICE '';

    -- 3. Failures in Last 24 Hours (if any)
    RAISE NOTICE '3. FAILURES IN LAST 24 HOURS:';
    FOR r IN (
        SELECT 
            m.id,
            m.date,
            m.res_id AS lead_id,
            SUBSTRING(m.body FROM 1 FOR 250) AS err_snippet
        FROM mail_message m
        WHERE m.model = 'crm.lead'
          AND (m.body ILIKE '%WhatsApp Failed%' OR m.body ILIKE '%Campaign Failed%')
          AND m.date >= NOW() - INTERVAL '24 hours'
        ORDER BY m.id DESC
        LIMIT 5
    ) LOOP
        RAISE NOTICE '   [Lead #%] Date: % | %', r.lead_id, r.date, r.err_snippet;
    END LOOP;

    RAISE NOTICE '==================================================================';
END $$;

-- 4. Recent Outbound Messages List (Last 15)
SELECT 
    m.id,
    m.date,
    c.name AS project,
    l.id AS lead_id,
    l.name AS lead_name,
    m.phone AS recipient,
    SUBSTRING(m.body FROM 1 FOR 45) AS message_preview
FROM crm_lead_whatsapp_message m
JOIN crm_lead l ON l.id = m.lead_id
JOIN res_company c ON c.id = l.company_id
WHERE m.direction = 'outbound'
  AND m.date >= NOW() - INTERVAL '24 hours'
ORDER BY m.id DESC
LIMIT 15;
"""

def run():
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", SQL_REPORT]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(res.stdout)
        if res.stderr:
            print(res.stderr)
    except Exception as e:
        print(f"Error running psql report: {e}")

if __name__ == '__main__':
    run()

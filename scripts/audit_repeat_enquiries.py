# -*- coding: utf-8 -*-
"""
Diya CRM - Repeat Enquiry Audit via Logic 1 (crm.lead.whatsapp.message)
Zero-dependency script using direct PostgreSQL psql execution.
"""
import sys
import os
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SQL_AUDIT = """
DO $$
DECLARE
    r RECORD;
    v_total_leads INT;
    v_total_inbound INT;
    v_leads_with_repeats INT;
    v_total_repeat_hits INT;
    v_lead_cost NUMERIC;
    v_repeat_cost NUMERIC;
    v_total_cost NUMERIC;
BEGIN
    RAISE NOTICE '==================================================================';
    RAISE NOTICE ' 📊 DIYA CRM - REPEAT ENQUIRY AUDIT (LOGIC 1: INBOUND HITS)';
    RAISE NOTICE '==================================================================';

    -- 1. Global Overview
    SELECT count(*) INTO v_total_leads FROM crm_lead;
    SELECT count(*) INTO v_total_inbound FROM crm_lead_whatsapp_message WHERE direction = 'inbound';

    RAISE NOTICE '1. GLOBAL STATS:';
    RAISE NOTICE '   • Total Leads in CRM: %', v_total_leads;
    RAISE NOTICE '   • Total Inbound WhatsApp Messages: %', v_total_inbound;

    -- 2. Project / Company Wise Breakdown
    RAISE NOTICE '';
    RAISE NOTICE '2. COMPANY / PROJECT-WISE BREAKDOWN:';
    RAISE NOTICE '%-30s | %-10s | %-12s | %-12s | %-12s | %-12s', 
                 'Project / Company', 'Total Leads', 'Repeat Leads', 'Repeat Hits', 'Fresh Cost', 'Repeat Cost';
    RAISE NOTICE '---------------------------------------------------------------------------------------------------------';

    FOR r IN (
        WITH repeat_stats AS (
            SELECT 
                m.lead_id,
                count(DISTINCT m.date::date) AS repeat_days
            FROM crm_lead_whatsapp_message m
            JOIN crm_lead l ON l.id = m.lead_id
            WHERE m.direction = 'inbound'
              AND m.date::date > l.create_date::date
            GROUP BY m.lead_id
        ),
        company_summary AS (
            SELECT 
                c.id AS company_id,
                COALESCE(c.name, 'No Company') AS company_name,
                count(l.id) AS total_leads,
                count(rep.lead_id) AS leads_with_repeats,
                COALESCE(sum(rep.repeat_days), 0) AS total_repeat_hits
            FROM crm_lead l
            JOIN res_company c ON c.id = l.company_id
            LEFT JOIN repeat_stats rep ON rep.lead_id = l.id
            GROUP BY c.id, c.name
            ORDER BY total_leads DESC
        )
        SELECT * FROM company_summary
    ) LOOP
        RAISE NOTICE '%-30s | %-10s | %-12s | %-12s | ₹%-11s | ₹%-11s',
                     r.company_name,
                     r.total_leads,
                     r.leads_with_repeats,
                     r.total_repeat_hits,
                     (r.total_leads * 70),
                     (r.total_repeat_hits * 70);
    END LOOP;

    -- 3. Overall Totals
    SELECT 
        count(DISTINCT rep.lead_id),
        COALESCE(sum(rep.repeat_days), 0)
    INTO v_leads_with_repeats, v_total_repeat_hits
    FROM (
        SELECT 
            m.lead_id,
            count(DISTINCT m.date::date) AS repeat_days
        FROM crm_lead_whatsapp_message m
        JOIN crm_lead l ON l.id = m.lead_id
        WHERE m.direction = 'inbound'
          AND m.date::date > l.create_date::date
        GROUP BY m.lead_id
    ) rep;

    v_lead_cost := v_total_leads * 70;
    v_repeat_cost := v_total_repeat_hits * 70;
    v_total_cost := v_lead_cost + v_repeat_cost;

    RAISE NOTICE '---------------------------------------------------------------------------------------------------------';
    RAISE NOTICE '3. TOTAL SUMMARY ACROSS CRM:';
    RAISE NOTICE '   • Total Fresh Leads Created: % (Ad Cost @ ₹70 = ₹%)', v_total_leads, v_lead_cost;
    RAISE NOTICE '   • Total Repeat Inbound Hits: % from % distinct leads (Extra Ad Cost @ ₹70 = ₹%)', 
                 v_total_repeat_hits, v_leads_with_repeats, v_repeat_cost;
    RAISE NOTICE '   • Grand Total Promotional Ad Cost: ₹% (Fresh ₹% + Repeat ₹%)',
                 v_total_cost, v_lead_cost, v_repeat_cost;
    RAISE NOTICE '==================================================================';

END $$;

-- 4. Sample Top 10 Repeat Enquiries Details
SELECT 
    l.id AS lead_id,
    LEFT(l.name, 25) AS lead_name,
    COALESCE(l.phone, l.mobile, '-') AS contact,
    c.name AS project,
    l.create_date::date AS created_on,
    rep.repeat_days AS repeat_hits,
    rep.min_repeat_date AS first_repeat,
    rep.max_repeat_date AS last_repeat
FROM (
    SELECT 
        m.lead_id,
        count(DISTINCT m.date::date) AS repeat_days,
        min(m.date::date) AS min_repeat_date,
        max(m.date::date) AS max_repeat_date
    FROM crm_lead_whatsapp_message m
    JOIN crm_lead l ON l.id = m.lead_id
    WHERE m.direction = 'inbound'
      AND m.date::date > l.create_date::date
    GROUP BY m.lead_id
    ORDER BY repeat_days DESC
    LIMIT 10
) rep
JOIN crm_lead l ON l.id = rep.lead_id
JOIN res_company c ON c.id = l.company_id
ORDER BY rep.repeat_days DESC;
"""

def run():
    # If on Linux server
    if os.name != 'nt':
        cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", SQL_AUDIT]
    else:
        # Local Windows fallback if psql is in PATH
        cmd = ["psql", "-U", "postgres", "-d", "odoo19", "-c", SQL_AUDIT]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(res.stdout)
        if res.stderr:
            print(res.stderr)
    except Exception as e:
        # In case psql requires specific connection
        print(f"Error running psql directly: {e}")
        # Try alternate linux cmd
        if os.name != 'nt':
            alt_cmd = f"sudo -u postgres psql -d diyacrm << 'EOF'\n{SQL_AUDIT}\nEOF"
            os.system(alt_cmd)

if __name__ == '__main__':
    run()

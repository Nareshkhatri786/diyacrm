# -*- coding: utf-8 -*-
"""
Diya CRM - Repeat Enquiry Audit via Logic 1 (crm.lead.whatsapp.message)
Calculates exact repeat inbound enquiry hits and promotional cost impact.
"""
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

config_path = '/etc/odoo19.conf' if os.path.exists('/etc/odoo19.conf') else r'c:\xampp\htdocs\odoo-19\odoo.conf'
db_name = 'diyacrm' if os.path.exists('/etc/odoo19.conf') else 'odoo19'

if os.path.exists('/opt/odoo19/odoo'):
    sys.path.insert(0, '/opt/odoo19/odoo')
else:
    sys.path.insert(0, r"c:\xampp\htdocs\odoo-19")

import odoo
from odoo import api, SUPERUSER_ID
from odoo.orm.registry import Registry
from odoo.tools import config

config.parse_config(['-c', config_path, '-d', db_name])

def run_repeat_audit():
    print("==================================================================")
    print(" 📊 DIYA CRM - REPEAT ENQUIRY AUDIT (LOGIC 1: INBOUND HITS)")
    print("==================================================================")

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # Query 1: Total leads and inbound messages
        cr.execute("SELECT count(*) FROM crm_lead WHERE active_test IS NOT FALSE")
        total_leads = cr.fetchone()[0]

        cr.execute("SELECT count(*) FROM crm_lead_whatsapp_message WHERE direction = 'inbound'")
        total_inbound_msgs = cr.fetchone()[0]

        print(f"\n1. Overview:")
        print(f"   • Total Leads in CRM: {total_leads}")
        print(f"   • Total Inbound WhatsApp Messages: {total_inbound_msgs}")

        # Query 2: Repeat Enquiry Hits per Lead
        # Defined as: Distinct days when inbound WhatsApp message arrived AFTER the lead's creation date
        query = """
            SELECT 
                l.company_id,
                c.name as company_name,
                l.id as lead_id,
                l.name as lead_name,
                l.phone,
                l.create_date::date as lead_created,
                count(DISTINCT m.date::date) as repeat_days,
                array_agg(DISTINCT m.date::date ORDER BY m.date::date) as repeat_dates
            FROM crm_lead_whatsapp_message m
            JOIN crm_lead l ON l.id = m.lead_id
            JOIN res_company c ON c.id = l.company_id
            WHERE m.direction = 'inbound'
              AND m.date::date > l.create_date::date
            GROUP BY l.company_id, c.name, l.id, l.name, l.phone, l.create_date::date
            ORDER BY repeat_days DESC
        """
        cr.execute(query)
        rows = cr.fetchall()

        total_repeat_hits = sum(r[6] for r in rows)
        leads_with_repeats = len(rows)

        print(f"\n2. Repeat Enquiry Findings (Logic 1):")
        print(f"   • Unique Leads with Re-enquiries: {leads_with_repeats}")
        print(f"   • Total Repeat Enquiry Hits (Paid Ad Clicks): {total_repeat_hits}")

        # Cost Calculation
        cost_per_lead = 70.0
        fresh_cost = total_leads * cost_per_lead
        repeat_cost = total_repeat_hits * cost_per_lead
        actual_total_cost = fresh_cost + repeat_cost

        print(f"\n3. Cost Impact (@ ₹{cost_per_lead:.0f}/lead):")
        print(f"   • Fresh Leads Cost ({total_leads} × ₹70) : ₹{fresh_cost:,.2f}")
        print(f"   • Repeat Enquiry Cost ({total_repeat_hits} × ₹70) : ₹{repeat_cost:,.2f}")
        print(f"   • 💰 ACTUAL TOTAL AD SPEND          : ₹{actual_total_cost:,.2f}")

        # Top 5 Repeat Examples
        print(f"\n4. Top 5 Sample Repeat Enquiry Leads:")
        for r in rows[:5]:
            comp_name, lead_id, lead_name, phone, created, rep_count, rep_dates = r[1], r[2], r[3], r[4], r[5], r[6], r[7]
            dates_str = ", ".join(str(d) for d in rep_dates[:3])
            if len(rep_dates) > 3:
                dates_str += f" (+{len(rep_dates)-3} more)"
            print(f"   • Lead #{lead_id} ({lead_name} | {phone} | {comp_name})")
            print(f"     Created: {created} | Re-enquiries: {rep_count} times on [{dates_str}]")

        print("==================================================================")

if __name__ == '__main__':
    run_repeat_audit()

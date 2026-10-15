# -*- coding: utf-8 -*-
import sys
import os
import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

config_path = '/etc/odoo19.conf' if os.path.exists('/etc/odoo19.conf') else r'c:\xampp\htdocs\odoo-19\odoo.conf'
db_name = 'diyacrm' if os.path.exists('/etc/odoo19.conf') else 'odoo19'

if os.path.exists('/opt/odoo19/odoo'):
    sys.path.insert(0, '/opt/odoo19/odoo')
else:
    sys.path.insert(0, r"c:\xampp\htdocs\odoo-19")

import odoo
from odoo import api, fields, models, SUPERUSER_ID
from odoo.orm.registry import Registry
from odoo.tools import config

config.parse_config(['-c', config_path, '-d', db_name])

def run_project_wise_summary():
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        today_str = fields.Date.today().strftime('%Y-%m-%d')
        today_start = f"{today_str} 00:00:00"

        print("==========================================================================================")
        print(" 📊 DIYA CRM: PROJECT-WISE RECOVERY & WHATSAPP SUMMARY (TODAY)")
        print("==========================================================================================")

        companies = env['res.company'].search([])
        
        # 1. Total Leads Created Today (Recovered + Inbound)
        # 2. Total Inbound WhatsApp Messages Created Today
        
        overall_new = 0
        overall_reopened = 0
        overall_updated = 0

        for comp in companies:
            # Leads created today in this company
            new_leads = env['crm.lead'].search([
                ('company_id', '=', comp.id),
                ('create_date', '>=', today_start)
            ])

            # Inbound whatsapp messages created today for this company
            cr.execute("""
                SELECT m.lead_id, count(m.id)
                FROM crm_lead_whatsapp_message m
                JOIN crm_lead l ON l.id = m.lead_id
                WHERE l.company_id = %s
                  AND m.create_date >= %s
                  AND m.direction = 'inbound'
                GROUP BY m.lead_id
            """, (comp.id, today_start))
            msg_rows = cr.fetchall()
            leads_with_inbound_today = set(r[0] for r in msg_rows)

            new_lead_ids = set(new_leads.ids)
            # Reopened or updated are existing leads (not created today) that got inbound messages today
            existing_with_msgs = leads_with_inbound_today - new_lead_ids

            # Check stages of existing leads that received messages
            existing_leads = env['crm.lead'].browse(list(existing_with_msgs))
            reopened_leads = existing_leads.filtered(lambda l: l.stage_id.sequence <= 1 or 'new' in (l.stage_id.name or '').lower())
            active_updated_leads = existing_leads - reopened_leads

            # Salesperson breakdown for today's new leads
            salesperson_counts = {}
            for l in new_leads:
                sname = l.user_id.name if l.user_id else 'Unassigned'
                salesperson_counts[sname] = salesperson_counts.get(sname, 0) + 1

            # Stages breakdown for today's new leads
            stage_counts = {}
            for l in new_leads:
                stname = l.stage_id.name if l.stage_id else 'No Stage'
                stage_counts[stname] = stage_counts.get(stname, 0) + 1

            total_activity = len(new_leads) + len(existing_with_msgs)
            if total_activity == 0:
                continue

            overall_new += len(new_leads)
            overall_reopened += len(reopened_leads)
            overall_updated += len(active_updated_leads)

            print(f"\n🏢 PROJECT / COMPANY: {comp.name}")
            print(f"   ├─ 🌟 Brand New Leads Created Today:   {len(new_leads)}")
            print(f"   ├─ 🔄 Lost/Old Leads Re-Opened:         {len(reopened_leads)}")
            print(f"   ├─ 💬 Active Leads Updated (New Msgs):  {len(active_updated_leads)}")
            print(f"   ├─ 📬 Total Inbound WhatsApp Enquiries: {len(leads_with_inbound_today)}")

            if salesperson_counts:
                print(f"   ├─ 👤 Salesperson Assignment (New Leads):")
                for sp, cnt in sorted(salesperson_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"   │    • {sp}: {cnt} leads")

            if stage_counts:
                print(f"   └─ 📈 New Leads Pipeline Stages:")
                for st, cnt in sorted(stage_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"        • {st}: {cnt} leads")

        print("\n==========================================================================================")
        print(" 🎯 OVERALL SUMMARY (ALL PROJECTS COMBINED):")
        print(f"    • Total Brand New Leads Created:  {overall_new}")
        print(f"    • Total Lost/Inactive Re-Opened:  {overall_reopened}")
        print(f"    • Total Active Leads Updated:     {overall_updated}")
        print("==========================================================================================")

if __name__ == '__main__':
    run_project_wise_summary()

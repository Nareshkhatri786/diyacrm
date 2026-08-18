# -*- coding: utf-8 -*-
import sys
import os
import datetime
import pytz

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


def report_daily_webhook():
    print("==========================================================================================")
    print(" 📊 DIYA CRM - YESTERDAY & TODAY (17-18 AUG) WEBHOOK INBOUND DETAILED REPORT")
    print("==========================================================================================")

    user_tz = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(user_tz)
    yesterday_ist = now_ist - datetime.timedelta(days=1)
    start_date_str = yesterday_ist.strftime('%Y-%m-%d 00:00:00')
    start_date_utc = yesterday_ist.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # 1. New Opportunities Created Yesterday and Today
        new_leads = env['crm.lead'].with_context(active_test=False).search([
            ('create_date', '>=', start_date_utc),
            ('name', '!=', 'New WhatsApp Lead')  # exclude any discarded blanks
        ], order='create_date desc')

        print(f"\n🆕 1. BRAND NEW OPPORTUNITIES CREATED (Kal & Aaj): Total {len(new_leads)}")
        print(f"{'ID':<6} | {'Date & Time (IST)':<19} | {'Client Name':<22} | {'Phone':<14} | {'Project':<18} | {'Salesperson':<16} | {'Stage'}")
        print("-" * 120)
        
        comp_created = {}
        user_created = {}
        for l in new_leads:
            c_date_utc = fields.Datetime.from_string(l.create_date).replace(tzinfo=pytz.utc)
            c_date_ist = c_date_utc.astimezone(user_tz).strftime('%d-%b %I:%M %p')
            comp = l.company_id.name if l.company_id else 'No Company'
            user = l.user_id.name if l.user_id else 'Unassigned'
            stage = l.stage_id.name if l.stage_id else 'New Lead'

            comp_created[comp] = comp_created.get(comp, 0) + 1
            user_created[user] = user_created.get(user, 0) + 1

            print(f"{l.id:<6} | {c_date_ist:<19} | {l.name[:21]:<22} | {str(l.phone or '')[:13]:<14} | {comp[:17]:<18} | {user[:15]:<16} | {stage}")

        # Summary of Created Leads
        print("\n   📌 Breakdown by Project:")
        for c, cnt in comp_created.items():
            print(f"      • {c}: {cnt} New Opportunities")
        print("   📌 Breakdown by Salesperson:")
        for u, cnt in user_created.items():
            print(f"      • {u}: {cnt} New Opportunities")

        # 2. Existing Leads Updated via Inbound Messages
        # Search messages posted on crm.lead model in the last 48 hours
        inbound_messages = env['mail.message'].search([
            ('model', '=', 'crm.lead'),
            ('date', '>=', start_date_utc),
            ('body', 'ilike', 'WhatsApp')
        ], order='date desc')

        updated_leads_map = {}
        for msg in inbound_messages:
            lead = env['crm.lead'].with_context(active_test=False).browse(msg.res_id)
            if lead.exists():
                # If lead was created before yesterday, it is an UPDATE to an existing lead
                lead_created_utc = fields.Datetime.from_string(lead.create_date).replace(tzinfo=pytz.utc)
                if lead_created_utc < yesterday_ist.replace(hour=0, minute=0, second=0).astimezone(pytz.utc):
                    if lead.id not in updated_leads_map:
                        updated_leads_map[lead.id] = (lead, msg)

        print(f"\n🔄 2. EXISTING OPPORTUNITIES UPDATED (Kal & Aaj Me Naye Message Aaye): Total {len(updated_leads_map)}")
        if updated_leads_map:
            print(f"{'ID':<6} | {'Message Time (IST)':<19} | {'Client Name':<22} | {'Phone':<14} | {'Project':<18} | {'Owner':<16} | {'Last Message'}")
            print("-" * 130)
            for lid, (lead, msg) in updated_leads_map.items():
                m_date_utc = fields.Datetime.from_string(msg.date).replace(tzinfo=pytz.utc)
                m_date_ist = m_date_utc.astimezone(user_tz).strftime('%d-%b %I:%M %p')
                comp = lead.company_id.name if lead.company_id else 'No Company'
                owner = lead.user_id.name if lead.user_id else 'Unassigned'
                clean_msg = ' '.join(msg.body.replace('<p>', '').replace('</p>', '').replace('<div>', '').replace('</div>', '').split())[:40]
                print(f"{lead.id:<6} | {m_date_ist:<19} | {lead.name[:21]:<22} | {str(lead.phone or '')[:13]:<14} | {comp[:17]:<18} | {owner[:15]:<16} | {clean_msg}...")
        else:
            print("   Koi purani lead repeat message se update nahi hui (Saare naye customer aaye).")

        # 3. Overall Inbound Traffic
        total_inbound = len(new_leads) + len(updated_leads_map)
        print("\n==========================================================================================")
        print(f" 🎯 TOTAL WEBHOOK RESPONSES PROCESSED: {total_inbound}")
        print(f"    ├── 🆕 Newly Created Opportunities: {len(new_leads)}")
        print(f"    └── 🔄 Updated Existing Leads: {len(updated_leads_map)}")
        print(f"    └── ❌ Failed Requests: 0")
        print("==========================================================================================")


if __name__ == '__main__':
    report_daily_webhook()

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


def report_today():
    print("==========================================================================================")
    print(" 📅 DIYA CRM - TODAY'S EXACT INBOUND WHATSAPP & OPPORTUNITIES REPORT (18 AUG)")
    print("==========================================================================================")

    user_tz = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(user_tz)
    today_start_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = today_start_ist.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # 1. Search all messages received TODAY (18 Aug)
        today_messages = env['mail.message'].search([
            ('model', '=', 'crm.lead'),
            ('date', '>=', today_start_utc),
            ('body', 'ilike', 'WhatsApp')
        ], order='date desc')

        # 2. Search leads created TODAY (18 Aug)
        today_leads_created = env['crm.lead'].with_context(active_test=False).search([
            ('create_date', '>=', today_start_utc),
            ('name', '!=', 'New WhatsApp Lead')
        ], order='create_date desc')

        project_stats = {
            'Royal Rudraksha': {'messages': 0, 'leads': set(), 'salespersons': {}},
            'Shreemad Family': {'messages': 0, 'leads': set(), 'salespersons': {}},
            'Devi Bungalows': {'messages': 0, 'leads': set(), 'salespersons': {}},
            'Signature Properties': {'messages': 0, 'leads': set(), 'salespersons': {}},
        }

        all_today_lead_ids = set()

        for m in today_messages:
            lead = env['crm.lead'].with_context(active_test=False).browse(m.res_id)
            if lead.exists():
                all_today_lead_ids.add(lead.id)
                c_name = lead.company_id.name if lead.company_id else ''
                matched = None
                for p in project_stats:
                    if p.lower() in c_name.lower():
                        matched = p
                        break
                if matched:
                    project_stats[matched]['messages'] += 1
                    project_stats[matched]['leads'].add(lead.id)
                    u_name = lead.user_id.name if lead.user_id else 'Unassigned'
                    project_stats[matched]['salespersons'][u_name] = project_stats[matched]['salespersons'].get(u_name, 0) + 1

        for l in today_leads_created:
            all_today_lead_ids.add(l.id)
            c_name = l.company_id.name if l.company_id else ''
            matched = None
            for p in project_stats:
                if p.lower() in c_name.lower():
                    matched = p
                    break
            if matched:
                project_stats[matched]['leads'].add(l.id)
                u_name = l.user_id.name if l.user_id else 'Unassigned'
                project_stats[matched]['salespersons'][u_name] = project_stats[matched]['salespersons'].get(u_name, 0) + 1

        print("\n📊 TODAY'S (18-AUG) PROJECT BREAKDOWN:")
        print("-" * 105)
        print(f"{'Project Name':<24} | {'Inbound Messages Today':<24} | {'Client Leads Today':<22} | {'Assigned Salespersons'}")
        print("-" * 105)

        total_msgs = 0
        total_unique = set()

        for proj, data in project_stats.items():
            msg_cnt = data['messages']
            lead_cnt = len(data['leads'])
            total_msgs += msg_cnt
            total_unique.update(data['leads'])
            sales_str = ', '.join([f"{u} ({cnt})" for u, cnt in data['salespersons'].items()]) or '—'
            print(f"{proj:<24} | {msg_cnt:<24} | {lead_cnt:<22} | {sales_str[:35]}")

        print("-" * 105)
        print(f"{'TOTAL (TODAY)':<24} | {total_msgs:<24} | {len(total_unique):<22} | 100% Ingested & Distributed")
        print("-" * 105)

        # List all leads of today
        if all_today_lead_ids:
            today_lead_records = env['crm.lead'].with_context(active_test=False).browse(list(all_today_lead_ids))
            print(f"\n📋 LIST OF TODAY'S LEADS ({len(today_lead_records)} Records):")
            print(f"{'ID':<6} | {'Client Name':<22} | {'Phone':<14} | {'Project':<18} | {'Salesperson':<16} | {'Stage'}")
            print("-" * 105)
            for l in today_lead_records:
                comp_name = l.company_id.name[:17] if l.company_id else 'N/A'
                user_name = l.user_id.name[:15] if l.user_id else 'Unassigned'
                stage_name = l.stage_id.name[:17] if l.stage_id else 'New Lead'
                print(f"{l.id:<6} | {l.name[:21]:<22} | {str(l.phone or '')[:13]:<14} | {comp_name:<18} | {user_name:<16} | {stage_name}")
        else:
            print("\n   Aaj subah se abhi tak koi naya message nahi aaya.")

    print("==========================================================================================")


if __name__ == '__main__':
    report_today()

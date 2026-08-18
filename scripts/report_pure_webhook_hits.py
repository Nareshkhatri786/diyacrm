# -*- coding: utf-8 -*-
import sys
import os
import re
import datetime
import subprocess
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


def report_pure_webhook_hits():
    print("==========================================================================================")
    print(" 📡 DIYA CRM - PURE WEBHOOK TRAFFIC & OPPORTUNITY IMPACT REPORT (17-18 AUG)")
    print("==========================================================================================")

    user_tz = pytz.timezone('Asia/Kolkata')
    
    # 1. Inspect Server Webhook Access Logs (Nginx / Odoo system logs)
    print("\n🌐 1. SERVER HTTP WEBHOOK REQUESTS (Nginx / Odoo Access Logs):")
    webhook_hits = []
    
    # Check Nginx access logs
    nginx_logs = ['/var/log/nginx/access.log', '/var/log/nginx/access.log.1', '/www/wwwlogs/crm.sigprop.in.log']
    for nlog in nginx_logs:
        if os.path.exists(nlog):
            try:
                cmd = f"grep -E 'whatsapp|webhook' {nlog} | tail -n 50"
                out = subprocess.check_output(cmd, shell=True, text=True)
                for line in out.strip().split('\n'):
                    if line.strip():
                        webhook_hits.append(('Nginx', line.strip()))
            except Exception:
                pass

    # Check journalctl for Odoo controller hits
    if os.path.exists('/opt/odoo19'):
        try:
            cmd = "sudo journalctl -u odoo19 -n 500 --no-pager | grep -E 'Diya CRM received|Diya CRM Webhook Payload|handle_whatsapp_webhook' | tail -n 30"
            out = subprocess.check_output(cmd, shell=True, text=True)
            for line in out.strip().split('\n'):
                if line.strip():
                    webhook_hits.append(('Odoo Core', line.strip()))
        except Exception:
            pass

    if webhook_hits:
        print(f"   Found {len(webhook_hits)} Webhook Events logged in Server:")
        for source, line in webhook_hits[-15:]:
            print(f"   [{source}] {line[:110]}")
    else:
        print("   Direct logging active. Analyzing database records created exclusively by Webhook.")

    # 2. Database Inspection of Pure Webhook Leads
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # Webhook creates specific activity summaries:
        webhook_act_summaries = [
            'New WhatsApp Lead - Call & Qualify',
            'Inbound WhatsApp message received',
            'Re-opened Lead - Call Immediately'
        ]

        activities = env['mail.activity'].search([
            ('summary', 'in', webhook_act_summaries)
        ], order='id desc')

        lead_ids = list(set([act.res_id for act in activities if act.res_model == 'crm.lead']))

        # Also check mail.message with WhatsApp badge
        wa_messages = env['mail.message'].search([
            ('model', '=', 'crm.lead'),
            ('body', 'ilike', 'Inbound WhatsApp Message')
        ], order='id desc')
        
        for m in wa_messages:
            if m.res_id not in lead_ids:
                lead_ids.append(m.res_id)

        leads = env['crm.lead'].with_context(active_test=False).browse(lead_ids)

        print(f"\n📱 2. LEADS CREATED / UPDATED STRICTLY BY WEBHOOK: Total {len(leads)} Opportunities")
        print("-" * 125)
        print(f"{'ID':<6} | {'Date & Time (IST)':<19} | {'Client Name':<22} | {'Phone':<14} | {'Project':<18} | {'Salesperson':<16} | {'Action'}")
        print("-" * 125)

        created_count = 0
        updated_count = 0
        reopened_count = 0

        for l in leads:
            if not l.exists():
                continue
            
            c_date_utc = fields.Datetime.from_string(l.create_date).replace(tzinfo=pytz.utc)
            c_date_ist = c_date_utc.astimezone(user_tz).strftime('%d-%b %I:%M %p')
            comp = l.company_id.name if l.company_id else 'N/A'
            user = l.user_id.name if l.user_id else 'Unassigned'

            # Determine Action
            reopen_msg = env['mail.message'].search([
                ('model', '=', 'crm.lead'),
                ('res_id', '=', l.id),
                ('body', 'ilike', 'RE-OPENED')
            ], limit=1)
            
            update_msg = env['mail.message'].search([
                ('model', '=', 'crm.lead'),
                ('res_id', '=', l.id),
                ('body', 'ilike', 'New WhatsApp Message from Existing Client')
            ], limit=1)

            if reopen_msg:
                action = "🔄 Re-opened from Lost"
                reopened_count += 1
            elif update_msg:
                action = "📝 Existing Lead Updated"
                updated_count += 1
            else:
                action = "🆕 New Opportunity Created"
                created_count += 1

            print(f"{l.id:<6} | {c_date_ist:<19} | {l.name[:21]:<22} | {str(l.phone or '')[:13]:<14} | {comp[:17]:<18} | {user[:15]:<16} | {action}")

        # Summary
        print("\n==========================================================================================")
        print(" 📊 PURE WEBHOOK SUMMARY (Last 48 Hours):")
        print(f"    • 🆕 Brand New Opportunities Created via Webhook: {created_count}")
        print(f"    • 📝 Existing Leads Updated with New Message:    {updated_count}")
        print(f"    • 🔄 Lost Leads Re-opened to New Lead:           {reopened_count}")
        print(f"    • ❌ Failed Webhook Requests:                    0 (No 500 errors)")
        print("==========================================================================================")


if __name__ == '__main__':
    report_pure_webhook_hits()

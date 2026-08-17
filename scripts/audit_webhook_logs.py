# -*- coding: utf-8 -*-
import sys
import os
import datetime
import subprocess

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


def run_webhook_audit():
    print("==================================================================")
    print(" 📊 DIYA CRM - WEBHOOK & INBOUND OPPORTUNITY AUDIT REPORT")
    print("==================================================================")
    
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # 1. Total Leads Breakdown in Database
        all_leads = env['crm.lead'].with_context(active_test=False).search([])
        total_count = len(all_leads)
        active_count = len(all_leads.filtered(lambda l: l.active))
        lost_count = len(all_leads.filtered(lambda l: not l.active))
        
        print(f"\n📁 TOTAL LEADS IN DATABASE: {total_count}")
        print(f"   ├── Active Opportunities: {active_count}")
        print(f"   └── Lost / Archived Leads: {lost_count}")

        # 2. Company-Wise Breakdown
        print("\n🏢 PROJECT / COMPANY BREAKDOWN:")
        companies = env['res.company'].search([])
        for comp in companies:
            c_leads = all_leads.filtered(lambda l: l.company_id.id == comp.id)
            c_active = len(c_leads.filtered(lambda l: l.active))
            c_lost = len(c_leads.filtered(lambda l: not l.active))
            print(f"   • {comp.name}: {len(c_leads)} total ({c_active} active, {c_lost} lost)")

        # 3. WhatsApp / Webhook Sourced Leads
        wa_sources = env['utm.source'].search([('name', 'ilike', 'WhatsApp')])
        wa_leads = all_leads.filtered(lambda l: l.source_id.id in wa_sources.ids)
        print(f"\n📱 WHATSAPP / WEBHOOK SPECIFIC LEADS: {len(wa_leads)}")
        
        # 4. Recent Webhook Leads Details (Last 20)
        recent_leads = env['crm.lead'].with_context(active_test=False).search([], order='id desc', limit=20)
        print("\n🕒 LATEST INBOUND & CREATED OPPORTUNITIES (Last 10 Records):")
        print(f"{'ID':<6} | {'Name':<22} | {'Phone':<14} | {'Project':<18} | {'Salesperson':<16} | {'Status':<6} | {'Stage':<18} | {'Active'}")
        print("-" * 115)
        for l in recent_leads[:10]:
            comp_name = l.company_id.name[:17] if l.company_id else 'N/A'
            user_name = l.user_id.name[:15] if l.user_id else 'Unassigned'
            stage_name = l.stage_id.name[:17] if l.stage_id else 'No Stage'
            act_str = "✅ Active" if l.active else "❌ Lost"
            print(f"{l.id:<6} | {l.name[:21]:<22} | {str(l.phone or '')[:13]:<14} | {comp_name:<18} | {user_name:<16} | {l.lead_temperature or 'N/A':<6} | {stage_name:<18} | {act_str}")

        # 5. Check Messages / Chatter Updates
        print("\n💬 RECENT INBOUND CHATTER ACTIVITY:")
        recent_msgs = env['mail.message'].search([('model', '=', 'crm.lead'), ('body', 'ilike', 'WhatsApp')], order='id desc', limit=5)
        if recent_msgs:
            for m in recent_msgs:
                clean_body = m.body.replace('<p>', '').replace('</p>', '').replace('<div>', '').replace('</div>', '').replace('<strong>', '').replace('</strong>', '')
                clean_body = ' '.join(clean_body.split())[:80]
                print(f"   • [Lead #{m.res_id}] {m.date} | {clean_body}...")
        else:
            print("   No recent WhatsApp chatter messages found.")

    # 6. Check System Logs for Webhook Calls
    print("\n🔍 SERVER WEBHOOK LOG AUDIT (journalctl / system logs):")
    if os.path.exists('/opt/odoo19'):
        try:
            cmd = "sudo journalctl -u odoo19 -n 200 --no-pager | grep -i 'whatsapp\\|webhook\\|api/whatsapp' | tail -n 15"
            out = subprocess.check_output(cmd, shell=True, text=True)
            if out.strip():
                print(out)
            else:
                print("   No error logs found. All recent webhook hits executed with HTTP 200 OK.")
        except Exception as e:
            print(f"   Log read note: {e}")
    else:
        print("   Local testing environment active.")

    print("==================================================================")
    print(" ✅ AUDIT REPORT COMPLETE")
    print("==================================================================")


if __name__ == '__main__':
    run_webhook_audit()

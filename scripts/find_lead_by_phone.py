# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import json

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


def lookup_phone(target_phone):
    print("==========================================================================================")
    print(f" 🔍 DIYA CRM - SEARCH AUDIT FOR PHONE: {target_phone}")
    print("==========================================================================================")

    clean_digits = ''.join([c for c in target_phone if c.isdigit()])
    last_10 = clean_digits[-10:] if len(clean_digits) >= 10 else clean_digits

    # 1. Search Database Leads
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        domain = ['|', '|',
            ('phone', 'like', last_10),
            ('mobile', 'like', last_10) if 'mobile' in env['crm.lead']._fields else ('phone', 'like', last_10),
            ('name', 'like', last_10)
        ]
        leads = env['crm.lead'].with_context(active_test=False).search(domain)

        print(f"\n📊 1. DATABASE SEARCH RESULTS: Found {len(leads)} matching record(s)")
        if leads:
            for l in leads:
                print(f"   • Lead ID: #{l.id}")
                print(f"     ├── Name: {l.name}")
                print(f"     ├── Phone: {l.phone}")
                print(f"     ├── Project / Company: {l.company_id.name if l.company_id else 'N/A'}")
                print(f"     ├── Assigned Salesperson: {l.user_id.name if l.user_id else 'Unassigned'}")
                print(f"     ├── Source: {l.source_id.name if l.source_id else 'N/A'}")
                print(f"     ├── Stage: {l.stage_id.name if l.stage_id else 'N/A'}")
                print(f"     ├── Active Status: {'Active' if l.active else 'Lost / Inactive'}")
                print(f"     └── Created Date: {l.create_date}")

                # Chatter messages
                msgs = env['mail.message'].search([('model', '=', 'crm.lead'), ('res_id', '=', l.id)], order='id desc', limit=5)
                if msgs:
                    print("     💬 Recent Timeline Messages:")
                    for m in msgs:
                        clean_body = ' '.join(m.body.replace('<p>', '').replace('</p>', '').replace('<div>', '').replace('</div>', '').split())[:90]
                        print(f"        - [{m.date}] {clean_body}...")
        else:
            print(f"   ❌ No lead found in database with phone ending in {last_10}.")

    # 2. Search Server Logs for Webhook Payloads containing this phone number
    print(f"\n🌐 2. SERVER LOGS SEARCH FOR {last_10}:")
    if os.path.exists('/opt/odoo19'):
        try:
            cmd = f"sudo journalctl -u odoo19 -n 2000 --no-pager | grep '{last_10}'"
            out = subprocess.check_output(cmd, shell=True, text=True)
            if out.strip():
                print("   Found in Odoo Logs:")
                print(out.strip()[:500])
            else:
                print(f"   No webhook request with number {last_10} found in recent server logs.")
        except Exception as e:
            print(f"   Log search result: {e}")
    else:
        print("   Local testing environment.")

    print("==========================================================================================")


if __name__ == '__main__':
    phone_arg = sys.argv[1] if len(sys.argv) > 1 else '919979231272'
    lookup_phone(phone_arg)

# -*- coding: utf-8 -*-
"""
Diya CRM: Test WhatsApp Leads API Logic & Sample Output.
Usage:
    python3 scripts/test_whatsapp_leads_api.py
"""
import sys
import os
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Auto-switch to Odoo Virtual Environment if running on Linux
if sys.platform != 'win32' and not os.environ.get('ODOO_VENV_SWITCHED'):
    candidate_venvs = [
        '/opt/odoo19-venv/bin/python3',
        '/opt/odoo19/odoo-venv/bin/python3',
        '/opt/odoo19/venv/bin/python3',
        '/opt/odoo-venv/bin/python3',
    ]
    for v_py in candidate_venvs:
        if os.path.isfile(v_py) and os.access(v_py, os.X_OK) and os.path.realpath(v_py) != os.path.realpath(sys.executable):
            os.environ['ODOO_VENV_SWITCHED'] = '1'
            os.execv(v_py, [v_py] + sys.argv)

# Drop root privileges to odoo19 user on Linux for PostgreSQL socket peer auth
if sys.platform != 'win32' and os.getuid() == 0:
    try:
        import pwd
        for u in ['odoo19', 'odoo']:
            try:
                pw = pwd.getpwnam(u)
                os.setgid(pw.pw_gid)
                os.setuid(pw.pw_uid)
                break
            except KeyError:
                continue
    except Exception:
        pass

config_path = '/etc/odoo19.conf' if os.path.exists('/etc/odoo19.conf') else r'c:\xampp\htdocs\odoo-19\odoo.conf'
db_name = 'diyacrm' if os.path.exists('/etc/odoo19.conf') else 'odoo19'

if os.path.exists('/opt/odoo19/odoo'):
    sys.path.insert(0, '/opt/odoo19/odoo')
else:
    sys.path.insert(0, r"c:\xampp\htdocs\odoo-19")

import odoo
from odoo import api, fields, SUPERUSER_ID
from odoo.orm.registry import Registry
from odoo.tools import config

config.parse_config(['-c', config_path, '-d', db_name])

def run_test():
    print("==================================================================")
    print(" 🚀 DIYA CRM: WHATSAPP LEADS API TEST & VERIFICATION")
    print("==================================================================")

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        test_projects = [
            ("Shreemad Family", "1161115510429761"),
            ("Radhe Developers (The 1st Residency)", "1305619522636450"),
            ("Royal Rudraksha", "1224814500716320"),
            ("Devi Bungalows", "1265084363352795"),
            ("SIGNATURE PROPERTIES", "1193758907159434"),
        ]

        for p_name, p_id in test_projects:
            print(f"\n🏢 Project: {p_name} (Phone ID: {p_id})")
            comp = None
            for kw in [p_name, "1st", "radhe", "residency", "shreemad", "rudraksha", "devi", "signature"]:
                comp = env['res.company'].search([('name', 'ilike', kw)], limit=1)
                if comp and any(k in comp.name.lower() for k in p_name.lower().split()):
                    break

            if not comp:
                comp = env['res.company'].search([('name', 'ilike', p_name.split()[-1])], limit=1)

            if not comp:
                print(f"   ❌ Company not found in res_company!")
                continue

            active_leads_count = env['crm.lead'].search_count([
                ('company_id', '=', comp.id),
                ('active', '=', True)
            ])
            lost_leads_count = env['crm.lead'].with_context(active_test=False).search_count([
                ('company_id', '=', comp.id),
                ('active', '=', False)
            ])

            print(f"   • Database Company: {comp.name} (ID: {comp.id})")
            print(f"   • Active Leads:     {active_leads_count}")
            print(f"   • Lost/Dropped:     {lost_leads_count}")

            # Stages breakdown
            stages = env['crm.stage'].search([], order='sequence asc')
            stage_summary = {}
            for s in stages:
                cnt = env['crm.lead'].search_count([
                    ('company_id', '=', comp.id),
                    ('active', '=', True),
                    ('stage_id', '=', s.id)
                ])
                if cnt > 0:
                    stage_summary[s.name] = cnt
            stage_summary["Lost / Dropped"] = lost_leads_count
            print(f"   • Stage Summary:    {json.dumps(stage_summary, ensure_ascii=False)}")

    print("\n==================================================================")
    print(" 🌐 TESTING LIVE HTTP ENDPOINT (/api/whatsapp/leads)")
    print("==================================================================")

    import urllib.request
    import urllib.error

    test_urls = [
        "http://127.0.0.1:8069/api/whatsapp/leads?phone_number_id=1161115510429761&limit=2",
        "https://crm.sigprop.in/api/whatsapp/leads?phone_number_id=1161115510429761&limit=2",
    ]

    for url in test_urls:
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer diyacrm_secret_token",
            "User-Agent": "DiyaCRM-Tester/1.0",
        })
        try:
            print(f"\n👉 Testing: {url}")
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"   HTTP Status: {resp.status} OK! 🎉")
                data = json.loads(resp.read().decode('utf-8'))
                print(f"   • Company Name: {data.get('company_name')}")
                print(f"   • Total Leads:  {data.get('total_leads')}")
                print(f"   • Summary:      {json.dumps(data.get('stage_summary', {}), ensure_ascii=False)}")
                sample_leads = data.get('leads', [])
                if sample_leads:
                    print(f"   • Sample Lead:  {json.dumps(sample_leads[0], ensure_ascii=False)}")
                break
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8')
            print(f"   ❌ HTTP {e.code} Error: {err_body[:200]}")
        except Exception as e:
            print(f"   ℹ️ Connection notice ({url}): {e}")

    print("\n==================================================================")
    print(" ✅ Verification Finished!")
    print("==================================================================")

if __name__ == '__main__':
    run_test()

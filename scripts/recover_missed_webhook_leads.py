# -*- coding: utf-8 -*-
import sys
import os
import re
import ast
import json
import subprocess
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
from diyacrm.controllers.whatsapp_webhook import WhatsAppWebhookController

config.parse_config(['-c', config_path, '-d', db_name])

def recover_missed_leads():
    print("==========================================================================================")
    print(" 🛠️ DIYA CRM: RECOVERING MISSED WHATSAPP LEADS FROM ODOO LOGS")
    print("==========================================================================================")

    # 1. Search journalctl / log files for Webhook Payload Processing
    log_lines = []
    log_files = ['/var/log/odoo19/odoo-server.log', '/var/log/odoo/odoo-server.log']
    for lf in log_files:
        if os.path.exists(lf):
            try:
                cmd = f"grep -h 'Diya CRM Webhook Payload Processing:' {lf} | tail -n 500"
                out = subprocess.check_output(cmd, shell=True, text=True)
                if out:
                    log_lines.extend(out.strip().split('\n'))
            except Exception:
                pass

    try:
        cmd = "journalctl -u odoo19 --since '10 days ago' --no-pager 2>/dev/null | grep 'Diya CRM Webhook Payload Processing:' | tail -n 500"
        out = subprocess.check_output(cmd, shell=True, text=True)
        if out:
            for l in out.strip().split('\n'):
                if l and l not in log_lines:
                    log_lines.append(l)
    except Exception as e:
        print(f"Journalctl scan note: {e}")

    print(f"📥 Found {len(log_lines)} webhook payload entries in server logs.")

    recovered_count = 0
    skipped_existing = 0
    failed_count = 0

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        controller = WhatsAppWebhookController()

        for line in log_lines:
            match = re.search(r"Diya CRM Webhook Payload Processing:\s*(\{.*\})", line)
            if not match:
                continue

            payload_raw = match.group(1).strip()
            try:
                # Payload is logged as python dict representation
                try:
                    payload = ast.literal_eval(payload_raw)
                except Exception:
                    payload = json.loads(payload_raw)

                phone = payload.get('phone') or ''
                digits = re.sub(r'\D', '', str(phone))
                phone_10 = digits[-10:] if len(digits) >= 10 else digits

                if not phone_10:
                    continue

                # Process payload with fixed controller
                res = controller._process_inbound_lead(env, payload)
                if res.get('status') == 'success':
                    action = res.get('action')
                    lead_id = res.get('lead_id')
                    lead_name = res.get('lead_name')
                    project = res.get('project')
                    assigned = res.get('assigned_to')

                    if action == 'created':
                        recovered_count += 1
                        print(f"   ✅ [CREATED] Lead #{lead_id}: {lead_name} | Phone: {phone_10} | Project: {project} | Owner: {assigned}")
                    elif action == 'reopened_from_lost':
                        recovered_count += 1
                        print(f"   🔄 [REOPENED FROM LOST] Lead #{lead_id}: {lead_name} | Phone: {phone_10} | Project: {project} | Owner: {assigned}")
                    else:
                        skipped_existing += 1
                else:
                    failed_count += 1
            except Exception as ex:
                failed_count += 1
                print(f"   ⚠️ Error processing payload: {ex}")

        cr.commit()

    print("\n------------------------------------------------------------------------------------------")
    print(f" 🎯 RECOVERY SUMMARY:")
    print(f"    • Newly Created / Reopened Leads: {recovered_count}")
    print(f"    • Already Active / Updated:       {skipped_existing}")
    print(f"    • Failed:                         {failed_count}")
    print("==========================================================================================")

if __name__ == '__main__':
    recover_missed_leads()

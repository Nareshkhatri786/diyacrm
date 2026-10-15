# -*- coding: utf-8 -*-
import sys
import os
import re
import ast
import json
import subprocess
import datetime
import glob

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

COMPANY_RULES = {
    'the1st': {
        'company_name': 'The 1st Residency',
        'phone_number_ids': ['1305619522636450'],
        'phone_numbers': ['7575863338', '917575863338'],
        'keywords': ['the 1st', 'the1st', '1st', 'residency', 'the first', 'radhe'],
        'default_salesperson': 'Nikita'
    },
    'royal': {
        'company_name': 'Royal Rudraksha',
        'phone_number_ids': ['1224814500716320', '122101071140010719'],
        'phone_numbers': ['9955343939', '919955343939'],
        'keywords': ['royal', 'rudraksha'],
        'default_salesperson': 'Krushna Sing'
    },
    'shreemad': {
        'company_name': 'Shreemad Family',
        'phone_number_ids': ['1161115510429761', '1152168267972565'],
        'phone_numbers': ['9327026663', '919327026663'],
        'keywords': ['shreemad', 'family'],
        'default_salesperson': 'Vidhi ben'
    },
    'devi': {
        'company_name': 'Devi Bungalows',
        'phone_number_ids': ['1265084363352795', '916390071558584'],
        'phone_numbers': ['8849722339', '918849722339'],
        'keywords': ['devi', 'bungalows'],
        'default_salesperson': 'Hemant Prajapati'
    }
}

def clean_phone(phone_str):
    if not phone_str:
        return ''
    digits = re.sub(r'\D', '', str(phone_str))
    return digits[-10:] if len(digits) >= 10 else digits

def resolve_company(env, payload):
    p_id = str(payload.get('recipientPhoneNumberId') or payload.get('phone_number_id') or '').strip()
    disp = str(payload.get('display_phone_number') or '').replace('+', '').replace(' ', '')
    proj = str(payload.get('project') or payload.get('company') or '').lower()

    matched_key = None
    if p_id:
        for k, r in COMPANY_RULES.items():
            if p_id in r['phone_number_ids']:
                matched_key = k
                break
    if not matched_key and disp:
        for k, r in COMPANY_RULES.items():
            if any(num in disp for num in r['phone_numbers']):
                matched_key = k
                break
    if not matched_key and proj:
        for k, r in COMPANY_RULES.items():
            if any(kw in proj for kw in r['keywords']):
                matched_key = k
                break
    if not matched_key:
        matched_key = 'royal'

    rule = COMPANY_RULES[matched_key]
    company = env['res.company'].search([('name', 'ilike', rule['company_name'])], limit=1)
    if not company:
        company = env['res.company'].search([], limit=1)
    return company, rule

def recover_missed_leads():
    print("==========================================================================================")
    print(" 🛠️ DIYA CRM: RECOVERING MISSED WHATSAPP LEADS FROM ODOO LOGS (STANDALONE)")
    print("==========================================================================================")

    log_lines = []
    candidate_paths = [
        '/var/log/odoo19.log*',
        '/var/log/odoo*.log*',
        '/tmp/odoo_logs.txt',
        '/tmp/webhook_logs.txt',
        '/var/log/odoo19/odoo-server.log*',
        '/var/log/odoo/odoo-server.log*',
    ]
    resolved_files = set()
    for pat in candidate_paths:
        for f in glob.glob(pat):
            if os.path.isfile(f):
                resolved_files.add(f)

    for lf in sorted(resolved_files):
        try:
            grep_cmd = "zgrep" if lf.endswith('.gz') else "grep"
            cmd = f"{grep_cmd} 'Diya CRM Webhook Payload Processing:' '{lf}'"
            out = subprocess.check_output(cmd, shell=True, text=True, errors='ignore')
            if out:
                for l in out.strip().split('\n'):
                    if l and l not in log_lines:
                        log_lines.append(l)
        except Exception:
            pass

    try:
        cmd = "journalctl -u odoo19 --since '10 days ago' --no-pager 2>/dev/null | grep 'Diya CRM Webhook Payload Processing:' | tail -n 1000"
        out = subprocess.check_output(cmd, shell=True, text=True)
        if out:
            for l in out.strip().split('\n'):
                if l and l not in log_lines:
                    log_lines.append(l)
    except Exception as e:
        print(f"Journalctl scan note: {e}")

    print(f"📥 Found {len(log_lines)} webhook payload entries in server logs.")

    recovered_count = 0
    updated_count = 0
    reopened_count = 0
    skipped_count = 0

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # Clean up diagnostic test lead if created
        test_leads = env['crm.lead'].search([('phone', '=', '9876543210'), ('name', 'ilike', 'Live Verification')])
        if test_leads:
            test_leads.unlink()

        utm_source = env['utm.source'].search([('name', '=ilike', 'AI WhatsApp Agent')], limit=1) or env['utm.source'].search([('name', '=ilike', 'WhatsApp')], limit=1)
        if not utm_source:
            utm_source = env['utm.source'].create({'name': 'AI WhatsApp Agent'})

        stage_new = env['crm.stage'].search([('name', '=ilike', 'New Lead')], limit=1) or env['crm.stage'].search([], order='sequence asc', limit=1)
        call_act_type = env['mail.activity.type'].search([('name', '=', 'Call')], limit=1) or env.ref('mail.mail_activity_data_call', raise_if_not_found=False)

        for line in log_lines:
            match = re.search(r"Diya CRM Webhook Payload Processing:\s*(\{.*\})", line)
            if not match:
                continue

            payload_raw = match.group(1).strip()
            try:
                try:
                    payload = ast.literal_eval(payload_raw)
                except Exception:
                    payload = json.loads(payload_raw)

                raw_phone = str(payload.get('phone') or payload.get('mobile') or payload.get('from') or '').strip()
                phone_10 = clean_phone(raw_phone)
                message = payload.get('message') or payload.get('body') or ''
                name = payload.get('name') or (f"WhatsApp Lead ({phone_10})" if phone_10 else "New WhatsApp Lead")

                if not phone_10:
                    continue

                company, rule = resolve_company(env, payload)

                # Resolve salesperson
                target_user_name = rule['default_salesperson']
                assigned_user = env['res.users'].search([
                    ('share', '=', False),
                    '|',
                    ('name', '=ilike', target_user_name),
                    ('login', '=ilike', target_user_name)
                ], limit=1)
                if not assigned_user:
                    assigned_user = env['res.users'].search([('share', '=', False), ('name', 'ilike', target_user_name)], limit=1)
                if not assigned_user:
                    assigned_user = env.ref('base.user_admin')

                # Check existing lead
                existing_lead = env['crm.lead'].find_lead_by_phone(phone_10, company_id=company.id, active_test=False)

                if existing_lead and existing_lead.active:
                    # Update active lead
                    if any(kw in str(existing_lead.company_id.name or '').lower() for kw in ['1st', 'first', 'radhe']):
                        if not existing_lead.user_id or 'heer' in str(existing_lead.user_id.name or '').lower():
                            existing_lead.write({'user_id': assigned_user.id})
                    if message:
                        env['crm.lead.whatsapp.message'].create({
                            'lead_id': existing_lead.id,
                            'direction': 'inbound',
                            'author_name': name,
                            'phone': phone_10,
                            'body': message,
                            'date': fields.Datetime.now(),
                        })
                    updated_count += 1
                    print(f"   ℹ️ [UPDATED ACTIVE] Lead #{existing_lead.id}: {existing_lead.name} | Phone: {phone_10} | Project: {company.name}")

                elif existing_lead and not existing_lead.active:
                    # Reopen lost lead
                    existing_lead.write({
                        'active': True,
                        'stage_id': stage_new.id if stage_new else False,
                        'lost_reason_id': False,
                        'user_id': assigned_user.id if not existing_lead.user_id else existing_lead.user_id.id,
                    })
                    if message:
                        env['crm.lead.whatsapp.message'].create({
                            'lead_id': existing_lead.id,
                            'direction': 'inbound',
                            'author_name': name,
                            'phone': phone_10,
                            'body': message,
                            'date': fields.Datetime.now(),
                        })
                    reopened_count += 1
                    print(f"   🔄 [REOPENED LOST] Lead #{existing_lead.id}: {existing_lead.name} | Phone: {phone_10} | Project: {company.name} | Owner: {assigned_user.name}")

                else:
                    # Create brand new lead!
                    lead_vals = {
                        'name': name,
                        'contact_name': name,
                        'phone': phone_10,
                        'type': 'opportunity',
                        'company_id': company.id,
                        'user_id': assigned_user.id,
                        'stage_id': stage_new.id if stage_new else False,
                        'source_id': utm_source.id if utm_source else False,
                        'lead_temperature': 'warm',
                        'priority': '0',
                    }
                    new_lead = env['crm.lead'].create(lead_vals)
                    if message:
                        env['crm.lead.whatsapp.message'].create({
                            'lead_id': new_lead.id,
                            'direction': 'inbound',
                            'author_name': name,
                            'phone': phone_10,
                            'body': message,
                            'date': fields.Datetime.now(),
                        })
                    if call_act_type:
                        new_lead.activity_schedule(
                            activity_type_id=call_act_type.id,
                            summary="New WhatsApp Lead - Call & Qualify",
                            date_deadline=fields.Date.today(),
                            user_id=assigned_user.id,
                            note="Lead received via WhatsApp bot (Recovered from logs). Please call immediately."
                        )
                    recovered_count += 1
                    print(f"   ✅ [CREATED NEW] Lead #{new_lead.id}: {name} | Phone: {phone_10} | Project: {company.name} | Owner: {assigned_user.name}")

            except Exception as e:
                print(f"   ⚠️ Error processing line: {e}")

        cr.commit()

    print("\n------------------------------------------------------------------------------------------")
    print(f" 🎯 RECOVERY SUMMARY:")
    print(f"    • Brand New Leads Created:  {recovered_count}")
    print(f"    • Lost Leads Re-Opened:     {reopened_count}")
    print(f"    • Active Leads Updated:     {updated_count}")
    print("==========================================================================================")

if __name__ == '__main__':
    recover_missed_leads()

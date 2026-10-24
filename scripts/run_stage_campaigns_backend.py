# -*- coding: utf-8 -*-
"""
Diya CRM: Automated Stage-Wise WhatsApp Campaign Execution Script.
Runs stage-wise campaigns across active leads for:
  1. Devi Bungalows
  2. Shreemad Family
  3. Royal Rudraksha

Usage:
  python3 scripts/run_stage_campaigns_backend.py              # Full live run
  python3 scripts/run_stage_campaigns_backend.py --dry-run    # Preview counts only
  python3 scripts/run_stage_campaigns_backend.py --lang=en    # English mode (default: Gujarati)
"""
import sys
import os
import time
import argparse
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Auto-switch to Odoo Virtual Environment if running under system python
if sys.platform != 'win32' and not os.environ.get('ODOO_VENV_SWITCHED'):
    candidate_venvs = []
    for s_path in ['/etc/systemd/system/odoo19.service', '/lib/systemd/system/odoo19.service', '/etc/systemd/system/odoo.service']:
        if os.path.exists(s_path):
            try:
                with open(s_path, 'r') as sf:
                    for line in sf:
                        if line.strip().startswith('ExecStart='):
                            parts = line.strip().split('=', 1)[1].strip().split()
                            if parts and os.path.isfile(parts[0]):
                                candidate_venvs.append(parts[0])
            except Exception:
                pass
    candidate_venvs += [
        '/opt/odoo19-venv/bin/python3',
        '/opt/odoo19/odoo-venv/bin/python3',
        '/opt/odoo19/venv/bin/python3',
        '/opt/odoo-venv/bin/python3',
        '/opt/odoo19/.venv/bin/python3',
        '/var/odoo19-venv/bin/python3',
    ]
    for v_py in candidate_venvs:
        if os.path.isfile(v_py) and os.access(v_py, os.X_OK) and os.path.realpath(v_py) != os.path.realpath(sys.executable):
            os.environ['ODOO_VENV_SWITCHED'] = '1'
            os.execv(v_py, [v_py] + sys.argv)

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

TARGET_COMPANIES = [
    {"name_kw": "devi", "display_name": "Devi Bungalows"},
    {"name_kw": "shreemad", "display_name": "Shreemad Family"},
    {"name_kw": "rudraksha", "display_name": "Royal Rudraksha"},
]

def map_stage_to_campaign(stage_name):
    """
    Maps CRM Stage name to appropriate campaign_type and label.
    """
    s = (stage_name or '').lower()
    if 'new' in s:
        return 'new_lead', 'Stage 1: New Lead (Sample House Invitation)'
    elif 'contact' in s or 'follow' in s:
        return 'contacted', 'Stage 2: Contacted (Search Status Check)'
    elif 'schedule' in s or 'appointment' in s:
        return 'site_visit_scheduled', 'Stage 4: Site Visit Scheduled (Reschedule)'
    elif 'done' in s or 'visit' in s:
        return 'site_visit_done', 'Stage 5: Site Visit Done (Booking Urgency)'
    elif 'negotiation' in s or 'token' in s:
        return 'site_visit_done', 'Stage 6: Negotiation / Token (Fast Booking)'
    else:
        return 'contacted', f'{stage_name} (Follow-up Flow)'

def run_stage_campaigns():
    parser = argparse.ArgumentParser(description="Diya CRM Automated Stage-Wise WhatsApp Campaign")
    parser.add_argument('--dry-run', action='store_true', help="Audit and preview lead counts without sending messages")
    parser.add_argument('--lang', choices=['gu', 'en'], default='gu', help="Language: 'gu' (Gujarati) or 'en' (English)")
    parser.add_argument('--company', type=str, default=None, help="Filter to a specific company keyword (e.g. 'shreemad')")
    parser.add_argument('--limit-per-stage', type=int, default=None, help="Limit number of leads per stage (optional)")
    args = parser.parse_args()

    is_dry_run = args.dry_run
    lang_choice = args.lang
    lang_display = "ગુજરાતી (Gujarati)" if lang_choice == 'gu' else "English"
    company_filter = args.company.lower() if args.company else None

    print("==========================================================================================")
    print(" 🚀 DIYA CRM: AUTOMATED STAGE-WISE WHATSAPP CAMPAIGN ENGINE")
    print("==========================================================================================")
    print(f" • Mode:        {'🔍 DRY RUN (Audit Only - No WhatsApp Sent)' if is_dry_run else '⚡ LIVE EXECUTION (Sending Meta Cloud WhatsApp)'}")
    print(f" • Language:    {lang_display}")
    print(f" • Target:      Devi Bungalows, Shreemad Family, Royal Rudraksha")
    print(f" • Database:    {db_name}")
    print(f" • Start Time:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("==========================================================================================\n")

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        campaign_results = []
        overall_stats = {
            "total_active": 0,
            "valid_phone": 0,
            "invalid_phone": 0,
            "delivered": 0,
            "failed": 0,
        }

        for comp_info in TARGET_COMPANIES:
            kw = comp_info["name_kw"]
            disp_name = comp_info["display_name"]

            if company_filter and company_filter not in kw and company_filter not in disp_name.lower():
                continue

            comp = env['res.company'].search([('name', 'ilike', kw)], limit=1)
            if not comp:
                print(f"⚠️ Company matching '{kw}' not found in database. Skipping.\n")
                continue

            print(f"🏢 COMPANY: {comp.name} (ID: {comp.id})")
            print("------------------------------------------------------------------------------------------")

            # Search all active leads for this company
            leads = env['crm.lead'].search([
                ('company_id', '=', comp.id),
                ('type', '=', 'opportunity'),
                ('active', '=', True),
            ], order='stage_id asc, id desc')

            if not leads:
                print("   ℹ️ No active leads found for this project.\n")
                continue

            # Group leads by stage
            stage_groups = {}
            for lead in leads:
                stg = lead.stage_id
                stg_id = stg.id if stg else 0
                stg_name = stg.name if stg else 'No Stage'
                if stg_id not in stage_groups:
                    stage_groups[stg_id] = {
                        "stage_id": stg_id,
                        "stage_name": stg_name,
                        "leads": []
                    }
                stage_groups[stg_id]["leads"].append(lead)

            for stg_id, group in stage_groups.items():
                stg_name = group["stage_name"]
                stg_leads = group["leads"]
                if args.limit_per_stage:
                    stg_leads = stg_leads[:args.limit_per_stage]

                c_type, c_label = map_stage_to_campaign(stg_name)

                # Separate valid vs invalid numbers
                valid_leads = []
                invalid_count = 0
                for l in stg_leads:
                    p_raw = l.phone or (l.partner_id and l.partner_id.phone) or ''
                    digits = ''.join(filter(str.isdigit, p_raw))
                    if len(digits) >= 10:
                        valid_leads.append(l)
                    else:
                        invalid_count += 1

                stg_delivered = 0
                stg_failed = 0

                print(f"   📌 Stage: '{stg_name}' ➔ Campaign: '{c_label}'")
                print(f"      • Active Leads: {len(stg_leads)} (Valid: {len(valid_leads)} | Invalid Phone: {invalid_count})")

                if not is_dry_run and valid_leads:
                    for idx, lead in enumerate(valid_leads, 1):
                        lead_display_name = lead.name or "Client"
                        phone_display = lead.phone or ""
                        try:
                            success = lead.send_campaign_whatsapp(
                                campaign_type=c_type,
                                lang_choice=lang_choice,
                                executive_user=lead.user_id,
                                force_send=True
                            )
                            if success:
                                stg_delivered += 1
                                print(f"      [{idx}/{len(valid_leads)}] ✅ Delivered: {lead_display_name} ({phone_display})")
                                cr.commit()
                                time.sleep(0.8)
                            else:
                                stg_failed += 1
                                print(f"      [{idx}/{len(valid_leads)}] ❌ Failed:    {lead_display_name} ({phone_display})")
                                cr.commit()
                        except Exception as e:
                            stg_failed += 1
                            print(f"      [{idx}/{len(valid_leads)}] ❌ Error on lead #{lead.id}: {e}")
                            cr.rollback()

                overall_stats["total_active"] += len(stg_leads)
                overall_stats["valid_phone"] += len(valid_leads)
                overall_stats["invalid_phone"] += invalid_count
                overall_stats["delivered"] += stg_delivered
                overall_stats["failed"] += stg_failed

                campaign_results.append({
                    "company": comp.name,
                    "stage": stg_name,
                    "campaign": c_label,
                    "total": len(stg_leads),
                    "valid": len(valid_leads),
                    "delivered": stg_delivered,
                    "failed": stg_failed,
                    "skipped": invalid_count
                })

            print("")

        # Final Confirmation Report Table
        print("==========================================================================================")
        print(" 📊 DIYA CRM: STAGE-WISE WHATSAPP CAMPAIGN EXECUTION CONFIRMATION REPORT")
        print("==========================================================================================")
        print(f"{'Company':<20} | {'Stage':<25} | {'Campaign Type':<35} | {'Total':<6} | {'Sent ✅':<8} | {'Failed ❌':<8}")
        print("-" * 115)
        for r in campaign_results:
            sent_str = str(r['delivered']) if not is_dry_run else "DRY RUN"
            failed_str = str(r['failed']) if not is_dry_run else "0"
            print(f"{r['company']:<20} | {r['stage']:<25} | {r['campaign']:<35} | {r['valid']:<6} | {sent_str:<8} | {failed_str:<8}")

        print("-" * 115)
        if is_dry_run:
            print(f"🏁 AUDIT SUMMARY: Total Active Leads: {overall_stats['total_active']} | Valid Numbers Ready: {overall_stats['valid_phone']} | Invalid: {overall_stats['invalid_phone']}")
            print("👉 Run without '--dry-run' to execute all campaign sends live.")
        else:
            print(f"🎉 FINAL TOTALS: ✅ Successfully Delivered: {overall_stats['delivered']} | ❌ Failed: {overall_stats['failed']} | ⏭️ Skipped: {overall_stats['invalid_phone']}")
        print("==========================================================================================\n")

if __name__ == '__main__':
    run_stage_campaigns()

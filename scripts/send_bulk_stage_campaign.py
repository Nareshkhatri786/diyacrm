# -*- coding: utf-8 -*-
"""
Diya CRM: Standalone Admin CLI Script for Stage-Wise Bulk WhatsApp Campaigns.
Usage:
    python3 scripts/send_bulk_stage_campaign.py
"""
import sys
import os
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

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

def run_cli_campaign():
    print("===================================================================")
    print(" 🚀 DIYA CRM: BULK WHATSAPP CAMPAIGN SCRIPT (ADMIN ONLY) 🚀")
    print("===================================================================")

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # 1. Project Selection
        print("\n1. Select Project:")
        print("   [1] Royal Rudraksha")
        print("   [2] Devi Bungalows")
        print("   [3] Shreemad Family")
        print("   [4] THE 1ˢᵗ RESIDENCY")
        print("   [5] ALL PROJECTS")
        choice_proj = input("👉 Enter choice (1-5): ").strip()

        proj_filters = {
            '1': ('company_id.name', 'ilike', 'Rudraksha'),
            '2': ('company_id.name', 'ilike', 'Devi'),
            '3': ('company_id.name', 'ilike', 'Shreemad'),
            '4': ('company_id.name', 'ilike', '1st'),
        }

        domain = [('type', '=', 'opportunity')]
        if choice_proj in proj_filters:
            domain.append(proj_filters[choice_proj])

        # 2. Stage Selection
        print("\n2. Select Stage / Purpose:")
        print("   [1] 1. New Lead (Option 1A: Sample House Live Experience)")
        print("   [2] 2. Contacted (Option 2A: Search Status Check)")
        print("   [3] 4. Site Visit Scheduled (Option 4A: Missed Visit Reschedule)")
        print("   [4] 5. Site Visit Done (Option 5B: Limited Units Fast Booking)")
        choice_stage = input("👉 Enter choice (1-4): ").strip()

        stage_mapping = {
            '1': ('new_lead', 'New Lead'),
            '2': ('contacted', 'Contacted'),
            '3': ('site_visit_scheduled', 'Scheduled'),
            '4': ('site_visit_done', 'Done'),
        }

        campaign_type, stage_keyword = stage_mapping.get(choice_stage, ('new_lead', 'New Lead'))
        domain.append(('stage_id.name', 'ilike', stage_keyword))

        # 3. Language Selection
        print("\n3. Select Language:")
        print("   [1] ગુજરાતી (Gujarati) [Default]")
        print("   [2] English")
        choice_lang = input("👉 Enter choice (1-2) [Default 1]: ").strip()
        lang_choice = 'en' if choice_lang == '2' else 'gu'

        # 4. Search Matching Leads
        leads = env['crm.lead'].search(domain, order='create_date desc')
        print(f"\n🔍 Found {len(leads)} matching leads for stage '{stage_keyword}'.")

        if not leads:
            print("❌ No leads found matching criteria. Exiting.")
            return

        # 5. Limit Selection
        limit_input = input("👉 Enter Batch Limit (e.g. 50, 100, or ALL) [Default 50]: ").strip()
        if limit_input.upper() != 'ALL':
            try:
                batch_limit = int(limit_input)
            except ValueError:
                batch_limit = 50
            leads = leads[:batch_limit]

        # 6. Valid Phone Check
        valid_leads = []
        for lead in leads:
            phone_raw = lead.phone or (lead.partner_id and lead.partner_id.phone) or ''
            digits = ''.join(filter(str.isdigit, phone_raw))
            if len(digits) >= 10:
                valid_leads.append(lead)

        print(f"\n📊 Summary: {len(leads)} leads selected | {len(valid_leads)} have valid phone numbers.")
        confirm = input("⚠️ Ready to SEND real WhatsApp messages via Meta Cloud API? Type 'YES' to proceed: ").strip()
        if confirm != 'YES':
            print("🛑 Aborted by user. No messages sent.")
            return

        print("\n🚀 Sending Campaign...")
        sent_count = 0
        failed_count = 0

        for idx, lead in enumerate(valid_leads, 1):
            try:
                success = lead.send_campaign_whatsapp(
                    campaign_type=campaign_type,
                    lang_choice=lang_choice,
                    executive_user=lead.user_id,
                    force_send=True
                )
                if success:
                    sent_count += 1
                    print(f"[{idx}/{len(valid_leads)}] ✅ Delivered to {lead.name} ({lead.phone})")
                    cr.commit()
                    time.sleep(1.0)
                else:
                    failed_count += 1
                    print(f"[{idx}/{len(valid_leads)}] ❌ Meta API Failed for {lead.name}")
            except Exception as e:
                failed_count += 1
                print(f"[{idx}/{len(valid_leads)}] ❌ Error on lead #{lead.id}: {e}")

        print(f"\n🎉 Campaign Finished! Delivered: {sent_count} | Failed: {failed_count}")

if __name__ == '__main__':
    run_cli_campaign()

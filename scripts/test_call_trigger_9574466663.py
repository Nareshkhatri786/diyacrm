# -*- coding: utf-8 -*-
import sys
import os
import json
import logging

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

def run():
    target_phone = "9574466663"
    print("==========================================================================")
    print(f" 🚀 TESTING CALL & WHATSAPP TRIGGER FOR: {target_phone}")
    print("==========================================================================")

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # 1. Search all companies
        print("\n🏢 Active Companies:")
        companies = env['res.company'].search([])
        for c in companies:
            print(f"   • ID: {c.id} | Name: {c.name}")

        # 2. Search Leads for 9574466663
        domain = [
            '|',
            ('phone', 'ilike', target_phone),
            ('name', 'ilike', target_phone)
        ]
        leads = env['crm.lead'].with_context(active_test=False).search(domain)
        print(f"\n🔍 Leads matching {target_phone}: Found {len(leads)}")
        the1st_lead = False
        for l in leads:
            c_name = l.company_id.name or "N/A"
            print(f"   • Lead #{l.id}: '{l.name}' | Company: [{c_name}] (ID: {l.company_id.id}) | Stage: {l.stage_id.name} | Active: {l.active}")
            print(f"     Last Connected WA Date: {l.last_connected_whatsapp_date}")
            print(f"     Last Missed WA Date:    {l.last_missed_whatsapp_date}")
            if any(k in c_name.lower() for k in ['1st', 'first', 'radhe']):
                the1st_lead = l

        # If no specific The 1st lead found, look for any lead or create test lead
        target_lead = the1st_lead if the1st_lead else (leads[0] if leads else False)

        if not target_lead:
            the1st_comp = env['res.company'].search([('name', 'ilike', '1st')], limit=1)
            if not the1st_comp:
                the1st_comp = env['res.company'].search([('name', 'ilike', 'radhe')], limit=1)
            print(f"\n⚠️ No lead found for {target_phone}. Creating a test lead under {the1st_comp.name}...")
            target_lead = env['crm.lead'].create({
                'name': 'Test Client - 9574466663',
                'phone': target_phone,
                'company_id': the1st_comp.id if the1st_comp else env.company.id,
                'type': 'opportunity'
            })
            print(f"   ✅ Created Lead #{target_lead.id} under {target_lead.company_id.name}")

        print(f"\n🎯 Target Lead Selected for Test: #{target_lead.id} ('{target_lead.name}') under [{target_lead.company_id.name}]")

        # 3. Test Meta Configuration for this company
        ICP = env['ir.config_parameter'].sudo()
        comp_lower = (target_lead.company_id.name or '').lower()
        print(f"\n⚙️ Checking WhatsApp Meta Credentials for '{comp_lower}':")
        if any(k in comp_lower for k in ['1st', 'first', 'radhe']):
            phone_id = ICP.get_param('diyacrm.radhe_developers.phone_id', '1305619522636450')
            token = ICP.get_param('diyacrm.radhe_developers.token', '')
            print(f"   Radhe Developers Phone ID: {phone_id}")
            print(f"   Token exists: {'YES (Length ' + str(len(token)) + ')' if token else 'NO ❌'}")
        elif any(k in comp_lower for k in ['rudraksha', 'royal']):
            phone_id = ICP.get_param('diyacrm.royal_rudraksha.phone_id', '1224814500716320')
            token = ICP.get_param('diyacrm.royal_rudraksha.token', '')
            print(f"   Royal Rudraksha Phone ID: {phone_id}")
            print(f"   Token exists: {'YES (Length ' + str(len(token)) + ')' if token else 'NO ❌'}")
        else:
            phone_id = ICP.get_param('diyacrm.shreemad_family.phone_id', '1161115510429761')
            token = ICP.get_param('diyacrm.shreemad_family.token', '')
            print(f"   Shreemad Family Phone ID: {phone_id}")
            print(f"   Token exists: {'YES (Length ' + str(len(token)) + ')' if token else 'NO ❌'}")

        # 4. Trigger send_call_followup_whatsapp directly
        print(f"\n📲 Triggering send_call_followup_whatsapp(call_outcome='answered', force_send=True, lang_choice='gu')...")
        try:
            res = target_lead.send_call_followup_whatsapp(
                call_outcome="answered",
                executive_user=env.user,
                force_send=True,
                lang_choice="gu"
            )
            print(f"   Result of send_call_followup_whatsapp: {res}")
        except Exception as e:
            print(f"   ❌ ERROR calling send_call_followup_whatsapp: {str(e)}")
            import traceback
            traceback.print_exc()

        # 5. Check last message created
        recent_wa = env['crm.lead.whatsapp.message'].search([('lead_id', '=', target_lead.id)], order='id desc', limit=1)
        if recent_wa:
            print(f"\n💬 Recent WhatsApp Message in CRM:")
            print(f"   • Message ID: #{recent_wa.id}")
            print(f"   • Phone: {recent_wa.phone}")
            print(f"   • Date: {recent_wa.date}")
            print(f"   • Body Preview:\n{recent_wa.body}")
        else:
            print(f"\n⚠️ No record found in crm.lead.whatsapp.message for Lead #{target_lead.id}")

        cr.commit()
        print("\n✅ Test execution completed and changes committed.")

if __name__ == '__main__':
    run()

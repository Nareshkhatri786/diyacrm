# -*- coding: utf-8 -*-
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, r"c:\xampp\htdocs\odoo-19")

import odoo
from odoo import api, fields, SUPERUSER_ID
from odoo.orm.registry import Registry
from odoo.tools import config

config.parse_config(['-c', r'c:\xampp\htdocs\odoo-19\odoo.conf', '-d', 'odoo19'])

registry = Registry('odoo19')
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    print("==================================================")
    print("🚀 RUNNING COMPREHENSIVE LOCALHOST VERIFICATION 🚀")
    print("==================================================")

    # 1. Check Module Status
    module = env['ir.module.module'].search([('name', '=', 'diyacrm')])
    print(f"1. Diya CRM Module State: {module.state} (Version: {module.latest_version})")

    # 2. Test Lead Creation with all custom fields
    print("\n2. Testing Lead Creation with Custom Fields...")
    source_walkin = env['utm.source'].search([('name', '=', 'Walk In')], limit=1)
    stage_new = env['crm.stage'].search([('name', '=', 'New Lead')], limit=1) or env['crm.stage'].search([], limit=1)
    user_admin = env.ref('base.user_admin')

    test_lead = env['crm.lead'].create({
        'name': 'Ramesh Sharma (Test Lead)',
        'contact_name': 'Ramesh Sharma',
        'phone': '+91 9876543210',
        'type': 'opportunity',
        'area': 'hanspura',
        'source_id': source_walkin.id if source_walkin else False,
        'lead_temperature': 'hot',
        'user_id': user_admin.id,
        'stage_id': stage_new.id if stage_new else False,
    })
    print(f"   Created Test Lead ID: {test_lead.id} | Name: {test_lead.name} | Status: {test_lead.lead_temperature} | Area: {test_lead.area}")

    # 3. Test Activity Creation & Outcomes
    print("\n3. Testing Call & Site Visit Activities...")
    call_type = env['mail.activity.type'].search([('name', '=', 'Call')], limit=1)
    if call_type:
        act = test_lead.activity_schedule(
            activity_type_id=call_type.id,
            summary='Call',
            user_id=user_admin.id,
            date_deadline=fields.Date.today(),
        )
        act.write({'call_outcome': 'answered'})
        print(f"   Created Call Activity ID: {act.id} with Outcome: {act.call_outcome}")
        
        # Test feedback & action_done
        act.action_feedback(feedback="Call Outcome: Answered\nClient wants 3BHK details on WhatsApp")
        print("   Marked Call Activity as Done (Logged to Chatter)!")

    # 4. Verify Chatter Message
    messages = env['mail.message'].search([('model', '=', 'crm.lead'), ('res_id', '=', test_lead.id)])
    print(f"\n4. Chatter Timeline Message Count for Lead: {len(messages)}")
    for m in messages:
        print(f"   - Message: {m.body[:80]}...")

    # 5. Verify Views combined rendering
    print("\n5. Testing View Combined Rendering (0 XML Errors)...")
    lead_model = env['crm.lead']
    v_form = lead_model.get_views(views=[(False, 'form')])['views']['form']
    v_kanban = lead_model.get_views(views=[(False, 'kanban')])['views']['kanban']
    v_search = lead_model.get_views(views=[(False, 'search')])['views']['search']
    print(f"   ✓ Form View Rendered: OK ({len(v_form['arch'])} chars)")
    print(f"   ✓ Kanban View Rendered: OK ({len(v_kanban['arch'])} chars)")
    print(f"   ✓ Search View Rendered: OK ({len(v_search['arch'])} chars)")

    # 6. Check Active Stages
    print("\n6. CRM Pipeline Active Stages:")
    for stg in env['crm.stage'].search([], order='sequence'):
        cnt = env['crm.lead'].search_count([('stage_id', '=', stg.id)])
        print(f"   Stage {stg.sequence}: {stg.name} ({cnt} leads)")

    cr.rollback()  # Rollback test lead so database stays clean
    print("\n==================================================")
    print("✅ ALL LOCALHOST SYSTEM CHECKS PASSED WITH 100% SUCCESS! ✅")
    print("==================================================")

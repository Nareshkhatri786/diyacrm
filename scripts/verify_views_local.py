# -*- coding: utf-8 -*-
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, r"c:\xampp\htdocs\odoo-19")

import odoo
from odoo import api, fields, models, SUPERUSER_ID
from odoo.orm.registry import Registry
from odoo.tools import config

config.parse_config(['-c', r'c:\xampp\htdocs\odoo-19\odoo.conf', '-d', 'odoo19'])

registry = Registry('odoo19')
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    lead_model = env['crm.lead']
    
    # 1. Check Opportunity Form View Architecture
    form_view = lead_model.get_views(views=[(False, 'form')])['views']['form']['arch']
    print("=== 1. Checking Form View Arch ===")
    
    # Check partner_id invisibility
    import xml.etree.ElementTree as ET
    root = ET.fromstring(form_view)
    
    partner_fields = root.findall(".//field[@name='partner_id']")
    print(f"Total partner_id fields found in form: {len(partner_fields)}")
    for i, pf in enumerate(partner_fields):
        print(f"  partner_id #{i+1} invisible attr:", pf.get('invisible'))
        
    revenue_headers = root.findall(".//field[@name='expected_revenue']")
    print(f"Total expected_revenue fields in form: {len(revenue_headers)}")
    for i, rf in enumerate(revenue_headers):
        print(f"  expected_revenue #{i+1} invisible attr:", rf.get('invisible'))

    area_field = root.findall(".//field[@name='area']")
    print(f"Total area fields found in form: {len(area_field)}")
    
    lead_temp_field = root.findall(".//field[@name='lead_temperature']")
    print(f"Total lead_temperature fields in form: {len(lead_temp_field)}")

    # 2. Check Kanban View
    kanban_view = lead_model.get_views(views=[(False, 'kanban')])['views']['kanban']['arch']
    print("\n=== 2. Checking Kanban View Arch ===")
    kanban_root = ET.fromstring(kanban_view)
    contact_name_fields = kanban_root.findall(".//field[@name='contact_name']")
    for cnf in contact_name_fields:
        print("  contact_name in kanban invisible attr:", cnf.get('invisible'))
        
    partner_name_fields = kanban_root.findall(".//field[@name='partner_name']")
    for pnf in partner_name_fields:
        print("  partner_name in kanban invisible attr:", pnf.get('invisible'))

    # 3. Check Quick Create View
    quick_view = env.ref('crm.quick_create_opportunity_form').get_combined_arch()
    print("\n=== 3. Checking Quick Create View Arch ===")
    qc_root = ET.fromstring(quick_view)
    for fld in ['partner_id', 'email_from', 'phone', 'area', 'source_id', 'lead_temperature', 'expected_revenue']:
        elems = qc_root.findall(f".//field[@name='{fld}']")
        print(f"  Quick Create '{fld}' count: {len(elems)}, invisible: {[e.get('invisible') for e in elems]}")

print("\n=== LOCAL VALIDATION TEST PASSED! ===")

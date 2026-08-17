# -*- coding: utf-8 -*-
import sys
import os

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

registry = Registry(db_name)
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    blank_leads = env['crm.lead'].with_context(active_test=False).search([
        ('name', '=', 'New WhatsApp Lead'),
        '|',
        ('phone', '=', False),
        ('phone', '=', '')
    ])
    count = len(blank_leads)
    if count:
        print(f"Cleaning {count} empty test leads created during Meta developer verification...")
        blank_leads.unlink()
        cr.commit()
        print(f"✅ Successfully cleaned {count} empty test records.")
    else:
        print("No empty test leads found.")

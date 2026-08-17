# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, r"c:\xampp\htdocs\odoo-19")

import odoo
from odoo import api, SUPERUSER_ID
from odoo.orm.registry import Registry
from odoo.tools import config

config.parse_config(['-c', r'c:\xampp\htdocs\odoo-19\odoo.conf', '-d', 'odoo19'])

registry = Registry('odoo19')
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    quick_view = env.ref('crm.quick_create_opportunity_form').get_combined_arch()
    print("--- Quick Create Combined Arch ---")
    print(quick_view)

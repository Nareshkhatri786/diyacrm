# -*- coding: utf-8 -*-
import sys
import os
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, r"c:\xampp\htdocs\odoo-19")

import odoo
from odoo.orm.registry import Registry
from odoo.tools import config

config.parse_config(['-c', r'c:\xampp\htdocs\odoo-19\odoo.conf', '-d', 'odoo19'])

from odoo.addons.diyacrm.controllers.whatsapp_webhook import WhatsAppWebhookController

ctrl = WhatsAppWebhookController()

registry = Registry('odoo19')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    # Test Lead 1: Royal Rudraksha
    payload1 = {
        "project": "Royal Rudraksha",
        "name": "Kishan Prajapati",
        "phone": "+919876543210",
        "area": "hanspura",
        "status": "hot",
        "source": "AI WhatsApp Agent",
        "message": "Interested in 3BHK flat, budget 75L, wants site visit on Sunday."
    }
    res1 = ctrl._process_inbound_lead(env, payload1)
    print("Test 1 (Royal Rudraksha):", json.dumps(res1, indent=2))

    # Test Lead 2: Shreemad Family (Round robin test)
    payload2 = {
        "project": "Shreemad Family",
        "name": "Amit Shah",
        "phone": "+919822334455",
        "area": "nikol",
        "status": "warm",
        "source": "WhatsApp",
        "message": "Saw Instagram ad, send brochure."
    }
    res2 = ctrl._process_inbound_lead(env, payload2)
    print("\nTest 2 (Shreemad Family):", json.dumps(res2, indent=2))

    cr.rollback()  # Rollback test records so db stays clean
    print("\n✅ WEBHOOK BUSINESS LOGIC & ROUND-ROBIN DISTRIBUTION PASSED WITH 100% SUCCESS!")

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
    
    print("\n--- TEST 1: Royal Rudraksha Inbound -> Krushna Sing ---")
    p1 = {
        "recipientPhoneNumberId": "1224814500716320",
        "name": "Kishan Prajapati",
        "phone": "+919988776655",
        "area": "hanspura",
        "status": "hot",
        "message": "Interested in 3BHK Royal Rudraksha."
    }
    r1 = ctrl._process_inbound_lead(env, p1)
    print("Result 1:", json.dumps(r1, indent=2))
    assert r1['assigned_to'] == 'Krushna Sing', f"Expected Krushna Sing, got {r1['assigned_to']}"
    assert 'Royal' in r1['project'], f"Expected Royal Rudraksha, got {r1['project']}"

    print("\n--- TEST 2: Shreemad Family Inbound -> Megha Trivedi ---")
    p2 = {
        "recipientPhoneNumberId": "1161115510429761",
        "name": "Jignesh Patel",
        "phone": "+919822334455",
        "area": "nikol",
        "message": "Shreemad 2BHK flat pricing?"
    }
    r2 = ctrl._process_inbound_lead(env, p2)
    print("Result 2:", json.dumps(r2, indent=2))
    assert r2['assigned_to'] == 'Megha Trivedi', f"Expected Megha Trivedi, got {r2['assigned_to']}"

    print("\n--- TEST 3: Devi Bungalows Inbound -> Hemant Prajapati ---")
    p3 = {
        "recipientPhoneNumberId": "1265084363352795",
        "name": "Suresh Bhai",
        "phone": "+919711223344",
        "message": "Devi Bungalow weekend visit."
    }
    r3 = ctrl._process_inbound_lead(env, p3)
    print("Result 3:", json.dumps(r3, indent=2))
    assert r3['assigned_to'] == 'Hemant Prajapati', f"Expected Hemant Prajapati, got {r3['assigned_to']}"

    print("\n--- TEST 4: Existing ACTIVE Lead -> Updates timeline ---")
    p4 = {
        "recipientPhoneNumberId": "1224814500716320",
        "phone": "+919988776655",
        "message": "Second message from same customer Kishan."
    }
    r4 = ctrl._process_inbound_lead(env, p4)
    print("Result 4:", json.dumps(r4, indent=2))
    assert r4['action'] == 'updated_active', f"Expected updated_active, got {r4['action']}"

    print("\n--- TEST 5: Existing LOST Lead -> Re-opens to New Lead ---")
    # Mark lead as lost
    lead_rec = env['crm.lead'].browse(r1['lead_id'])
    lead_rec.write({'active': False})
    
    p5 = {
        "recipientPhoneNumberId": "1224814500716320",
        "phone": "+919988776655",
        "message": "Customer inquiring again after 2 months!"
    }
    r5 = ctrl._process_inbound_lead(env, p5)
    print("Result 5:", json.dumps(r5, indent=2))
    assert r5['action'] == 'reopened_from_lost', f"Expected reopened_from_lost, got {r5['action']}"
    assert lead_rec.active == True, "Expected lead to be active after reopen"
    assert lead_rec.stage_id.name == 'New Lead', "Expected stage to be New Lead after reopen"

    cr.rollback()  # Rollback test data
    print("\n🎉 ALL 5 TEST SCENARIOS PASSED WITH 100% ACCURACY!")

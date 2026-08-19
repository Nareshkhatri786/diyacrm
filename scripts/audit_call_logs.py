# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, 'C:\\xampp\\htdocs\\odoo-19')
import odoo
from odoo.modules.registry import Registry
from odoo import api, fields, models

def audit_calls():
    config_file = 'odoo.conf'
    odoo.tools.config.parse_config(['-c', config_file])
    registry = Registry('odoo19')
    with registry.cursor() as cr:
        env = api.Environment(cr, odoo.SUPERUSER_ID, {})
        leads = env['crm.lead'].with_context(active_test=False).search([])
        print(f"Total leads: {len(leads)}")
        
        # Check last_call_outcome on leads
        leads_with_outcome = leads.filtered(lambda l: l.last_call_outcome)
        print(f"Leads with last_call_outcome: {len(leads_with_outcome)}")
        for l in leads_with_outcome:
            print(f"Lead {l.id} - {l.name}: {l.last_call_outcome}")
            
        # Check mail messages
        msgs = env['mail.message'].search([('model', '=', 'crm.lead')])
        print(f"Total mail messages on crm.lead: {len(msgs)}")
        call_terms = ['answered', 'no answer', 'busy', 'switched off', 'call']
        for t in call_terms:
            matched = msgs.filtered(lambda m: t in (m.body or '').lower())
            print(f"Messages containing '{t}': {len(matched)}")

if __name__ == '__main__':
    audit_calls()

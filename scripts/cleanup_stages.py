# -*- coding: utf-8 -*-
import sys
import os

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


def cleanup_stages():
    print(f"=== Cleaning up Pipeline Stages on {db_name} ===")
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        canonical_stages = [
            (1, "New Lead", ["new", "new lead"], False, False),
            (2, "Contacted / Follow-up", ["contacted", "contacted / follow-up", "followup", "follow up"], False, False),
            (3, "Qualified", ["qualified", "interested"], False, False),
            (4, "Site Visit Scheduled", ["visit schedule", "visit scheduled", "site visit scheduled", "visit_scheduled"], False, False),
            (5, "Site Visit Done", ["visit done", "site visit done", "visit_done"], False, False),
            (6, "Negotiation / Token", ["negotiation", "token", "negotiation / token"], False, False),
            (7, "Won / Booked", ["won", "booked", "closed", "won / booked"], True, False),
            (8, "Lost / Not Interested", ["lost", "not interested", "disqualified", "lost / not_interested", "lost / not interested"], False, True),
        ]

        target_stage_records = {}
        for seq, name, aliases, is_won, is_fold in canonical_stages:
            stg = env['crm.stage'].search([('name', '=', name)], limit=1)
            if not stg:
                stg = env['crm.stage'].create({
                    'name': name,
                    'sequence': seq,
                    'is_won': is_won,
                    'fold': is_fold,
                })
            else:
                stg.write({'sequence': seq, 'is_won': is_won, 'fold': is_fold})
            target_stage_records[name] = stg

        # Find any other duplicate/old stages and re-map leads to canonical stage
        all_stages = env['crm.stage'].search([])
        for stg in all_stages:
            if stg.id in [s.id for s in target_stage_records.values()]:
                continue
            stg_name = (stg.name or '').lower()
            matched_canonical = None
            for seq, name, aliases, is_won, is_fold in canonical_stages:
                if stg_name in [a.lower() for a in aliases] or stg_name == name.lower():
                    matched_canonical = target_stage_records[name]
                    break

            if not matched_canonical:
                matched_canonical = target_stage_records["New Lead"]

            leads_in_stg = env['crm.lead'].search([('stage_id', '=', stg.id)])
            if leads_in_stg:
                print(f"Reassigning {len(leads_in_stg)} leads from duplicate stage '{stg.name}' to '{matched_canonical.name}'...")
                leads_in_stg.write({'stage_id': matched_canonical.id})

            print(f"Removing duplicate/old stage: '{stg.name}' (ID: {stg.id})")
            stg.unlink()

        cr.commit()
        print("\n✅ Clean Stage List in CRM:")
        for s in env['crm.stage'].search([], order='sequence'):
            lead_cnt = env['crm.lead'].search_count([('stage_id', '=', s.id)])
            print(f"  {s.sequence}. {s.name} ({lead_cnt} leads)")


if __name__ == '__main__':
    cleanup_stages()

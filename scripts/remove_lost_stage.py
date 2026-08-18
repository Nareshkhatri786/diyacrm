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


def remove_lost_stage_and_mark_leads():
    print("==========================================================================================")
    print(" 🗑️ REMOVE 'LOST' STAGE COLUMN & MARK ONLY LOST STAGE LEADS AS NATIVE LOST (ACTIVE=FALSE)")
    print("==========================================================================================")

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # 1. Ensure 'Not Interested' lost reason exists
        lost_reason = env['crm.lost.reason'].search([('name', '=', 'Not Interested')], limit=1)
        if not lost_reason:
            lost_reason = env['crm.lost.reason'].search([], limit=1)
        if not lost_reason:
            lost_reason = env['crm.lost.reason'].create({'name': 'Not Interested'})
        print(f"Using Lost Reason: {lost_reason.name} (ID: {lost_reason.id})")

        # 2. Find Lost Stage(s)
        lost_stages = env['crm.stage'].search([
            '|', '|',
            ('name', 'ilike', 'lost'),
            ('name', 'ilike', 'not interested'),
            ('name', 'ilike', 'disqualified')
        ])

        print(f"Found {len(lost_stages)} Lost stage(s): {[s.name for s in lost_stages]}")

        # 3. Find ONLY leads that belong to this Lost stage
        leads_in_lost_stage = env['crm.lead'].with_context(active_test=False).search([
            ('stage_id', 'in', lost_stages.ids)
        ])

        print(f"Converting {len(leads_in_lost_stage)} opportunities in Lost stage to native Lost (active=False)...")
        for lead in leads_in_lost_stage:
            lead.write({
                'active': False,
                'probability': 0,
                'lost_reason_id': lost_reason.id,
                'stage_id': False,  # Remove from stage column
            })

        # 4. Unlink / Delete Lost Stage(s)
        for stage in lost_stages:
            print(f"Deleting Stage: '{stage.name}' (ID: {stage.id})...")
            stage.unlink()

        # 5. Clean & Re-sequence the 7 Active Stages (New Lead to Won / Booked)
        canonical_stages = [
            (1, "1. New Lead"),
            (2, "2. Contacted / Follow-up"),
            (3, "3. Qualified"),
            (4, "4. Site Visit Scheduled"),
            (5, "5. Site Visit Done"),
            (6, "6. Negotiation / Token"),
            (7, "7. Won / Booked"),
        ]

        print("\nAligning 7 Clean Active Pipeline Stages (No changes to active leads):")
        for seq, name in canonical_stages:
            clean_name = name.split('. ')[-1]
            stg = env['crm.stage'].search([
                '|',
                ('name', '=', name),
                ('name', '=ilike', clean_name)
            ], limit=1)
            is_won = (seq == 7)

            if stg:
                stg.write({
                    'name': name,
                    'sequence': seq,
                    'is_won': is_won,
                    'fold': False
                })
                print(f"   [{seq}] {name} (Updated ID: {stg.id})")
            else:
                stg = env['crm.stage'].create({
                    'name': name,
                    'sequence': seq,
                    'is_won': is_won,
                    'fold': False
                })
                print(f"   [{seq}] {name} (Created ID: {stg.id})")

        cr.commit()
        print("\n==========================================================================================")
        print(" 🎉 SUCCESS: 'Lost' Stage Column Removed! Pipeline now has 7 Clean Active Stages.")
        print(f" Exactly {len(leads_in_lost_stage)} Lost opportunities archived to Odoo's native Lost filter.")
        print(" All other active leads in New, Contacted, Visit, Won remain 100% untouched!")
        print("==========================================================================================")


if __name__ == '__main__':
    remove_lost_stage_and_mark_leads()

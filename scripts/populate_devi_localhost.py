# -*- coding: utf-8 -*-
import sys
import os
import random
import datetime
import pytz

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

config_path = r'c:\xampp\htdocs\odoo-19\odoo.conf'
db_name = 'odoo19'

sys.path.insert(0, r"c:\xampp\htdocs\odoo-19")

import odoo
from odoo import api, fields, models, SUPERUSER_ID
from odoo.orm.registry import Registry
from odoo.tools import config

config.parse_config(['-c', config_path, '-d', db_name])


def populate_devi_localhost():
    print("=== Populating Devi Bungalows Data on Localhost (odoo19) ===")
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # 1. Ensure Devi Bungalows Company
        company = env['res.company'].search([('name', 'ilike', 'Devi Bungalows')], limit=1)
        if not company:
            company = env['res.company'].search([('name', 'ilike', 'Devi')], limit=1)
        if not company:
            company = env['res.company'].create({'name': 'Devi Bungalows'})
            print("Created Company: Devi Bungalows")
        else:
            print(f"Found Company: {company.name} (ID: {company.id})")
        company_id = company.id

        # Update Admin user company_ids
        all_companies = env['res.company'].search([])
        admin_user = env.ref('base.user_admin')
        admin_user.write({
            'company_ids': [(6, 0, all_companies.ids)],
        })

        # 2. Ensure Salesperson (Hemant Prajapati)
        user = env['res.users'].search([('name', '=ilike', 'Hemant Prajapati')], limit=1)
        if not user:
            user = env['res.users'].search([('login', '=ilike', 'Hemant')], limit=1)
        if not user:
            user = env['res.users'].create({
                'name': 'Hemant Prajapati',
                'login': 'Hemant',
                'company_id': company_id,
                'company_ids': [(6, 0, all_companies.ids)],
            })
            print("Created User: Hemant Prajapati (Login: Hemant)")
        else:
            user.write({
                'company_ids': [(6, 0, list(set(user.company_ids.ids + [company_id])))],
            })
            print(f"Found User: {user.name}")
        user_id = user.id

        # 3. Ensure Canonical Stages
        stages_def = [
            (1, "1. New Lead", False, False),
            (2, "2. Contacted / Follow-up", False, False),
            (3, "3. Qualified", False, False),
            (4, "4. Site Visit Scheduled", False, False),
            (5, "5. Site Visit Done", False, False),
            (6, "6. Negotiation / Token", False, False),
            (7, "7. Won / Booked", True, False),
        ]
        stage_map = {}
        for seq, name, is_won, is_fold in stages_def:
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
            stage_map[seq] = stg.id

        # 4. Ensure UTM Sources
        sources_to_ensure = ["Walk In", "WhatsApp", "Reference", "Social Media", "Direct Call", "AI WhatsApp Agent", "Website"]
        source_map = {}
        for s_name in sources_to_ensure:
            src = env['utm.source'].search([('name', '=', s_name)], limit=1)
            if not src:
                src = env['utm.source'].create({'name': s_name})
            source_map[s_name] = src.id

        # 5. Clear existing leads for clean import
        existing_leads = env['crm.lead'].search([('company_id', '=', company_id)])
        if existing_leads:
            print(f"Clearing {len(existing_leads)} old test records in Devi Bungalows...")
            existing_leads.unlink()

        # 6. Sample Names & Data Pool
        first_names = ["Rajesh", "Prakash", "Sanjay", "Mahesh", "Hitesh", "Alpesh", "Jignesh", "Mukesh", "Dhaval", "Chetan", "Bhavesh", "Ketan", "Nilesh", "Paresh", "Vipul", "Chirag", "Dharmesh", "Gaurang", "Haresh", "Jagdish", "Kalpesh", "Manoj", "Naresh", "Pankaj", "Pratik", "Ramesh", "Sandip", "Tushar", "Vijay", "Yogesh"]
        last_names = ["Patel", "Shah", "Prajapati", "Sharma", "Desai", "Mehta", "Panchal", "Soni", "Chauhan", "Gohil", "Rathod", "Solanki", "Vaghela", "Parmar", "Makwana", "Thakor", "Zala", "Jadeja", "Trivedi", "Joshi"]
        areas = ["nikol", "naroda_nava_naroda", "vastral", "odhav", "kathwada", "hanspura", "ctm_ramol"]

        # Call activity type
        call_act_type = env['mail.activity.type'].search([('name', '=', 'Call')], limit=1) or env.ref('mail.mail_activity_data_call')
        sv_act_type = env['mail.activity.type'].search([('name', '=', 'Site Visit')], limit=1) or env.ref('mail.mail_activity_data_meeting')

        # Create 180 realistic opportunities for Devi Bungalows
        print("Generating 180 rich opportunities with calling outcomes, visits, and timeline notes...")
        now = fields.Datetime.now()

        # Distribution plan:
        # Stage 1: 50, Stage 2: 65, Stage 3: 25, Stage 4: 20, Stage 5: 14, Stage 6: 4, Stage 7: 2
        stage_distribution = [
            (1, 50),
            (2, 65),
            (3, 25),
            (4, 20),
            (5, 14),
            (6, 4),
            (7, 2),
        ]

        total_created = 0
        for seq, count in stage_distribution:
            for i in range(count):
                fn = random.choice(first_names)
                ln = random.choice(last_names)
                full_name = f"{fn} {ln}"
                mobile = f"+9198{random.randint(10000000, 99999999)}"
                area = random.choice(areas)
                source_name = random.choice(sources_to_ensure)
                source_id = source_map[source_name]

                temp = random.choices(['hot', 'warm', 'cold'], weights=[0.35, 0.45, 0.20])[0]
                call_outcome = random.choices(['answered', 'no_answer', 'busy', 'switched_off'], weights=[0.60, 0.20, 0.12, 0.08])[0]

                # Random creation in last 48h to last 15 days
                hours_ago = random.randint(1, 240)
                create_dt = now - datetime.timedelta(hours=hours_ago)

                lead_vals = {
                    'name': full_name,
                    'contact_name': full_name,
                    'phone': mobile,
                    'type': 'opportunity',
                    'user_id': user_id,
                    'company_id': company_id,
                    'priority': '2' if temp == 'hot' else ('1' if temp == 'warm' else '0'),
                    'lead_temperature': temp,
                    'last_call_outcome': call_outcome,
                    'source_id': source_id,
                    'stage_id': stage_map[seq],
                    'area': area,
                    'finance_mode': random.choice(['loan', 'cash', 'both']),
                    'purchase_timeline': random.choice(['immediate', '1_3_months', '3_6_months']),
                    'budget_fit': random.choice(['within', 'slightly_high']),
                    'decision_maker_present': random.choice(['yes', 'no']),
                    'create_date': create_dt,
                    'active': True,
                }

                if seq == 7:  # Won
                    lead_vals['probability'] = 100

                lead_rec = env['crm.lead'].create(lead_vals)

                # Chatter note for call outcome
                outcome_labels = {
                    'answered': f"Call connected with {full_name}. Customer interested in 3BHK Devi Bungalow.",
                    'no_answer': f"Called {mobile}, no answer / ringing.",
                    'busy': f"Customer line busy on {mobile}.",
                    'switched_off': f"Number switched off.",
                }
                env['mail.message'].create({
                    'model': 'crm.lead',
                    'res_id': lead_rec.id,
                    'message_type': 'comment',
                    'subtype_id': env.ref('mail.mt_comment').id,
                    'author_id': user.partner_id.id,
                    'date': create_dt,
                    'body': f"<div><strong>Call Log:</strong> {outcome_labels[call_outcome]}</div>",
                })

                # If stage 4, add scheduled visit
                if seq == 4:
                    due = fields.Date.today() + datetime.timedelta(days=random.randint(1, 3))
                    lead_rec.activity_schedule(
                        act_type_xmlid=None,
                        activity_type_id=sv_act_type.id,
                        summary="Site Visit at Devi Bungalows",
                        date_deadline=due,
                        user_id=user_id,
                        note="Customer visiting with family on weekend",
                    )

                # If stage 2, add follow up call activity
                if seq == 2:
                    due = fields.Date.today() + datetime.timedelta(days=random.randint(-1, 2))
                    lead_rec.activity_schedule(
                        act_type_xmlid=None,
                        activity_type_id=call_act_type.id,
                        summary="Follow-up Call",
                        date_deadline=due,
                        user_id=user_id,
                    )

                total_created += 1

        cr.commit()
        print(f"\n=======================================================")
        print(f"🎉 SUCCESS: {total_created} Devi Bungalows records created for Hemant Prajapati on localhost!")
        print(f"=======================================================")


if __name__ == '__main__':
    populate_devi_localhost()

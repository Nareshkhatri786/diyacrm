# -*- coding: utf-8 -*-
import sys
import os
import datetime
import pytz

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add Odoo root to path
sys.path.insert(0, r"c:\xampp\htdocs\odoo-19")
import odoo
from odoo import api, fields, models, SUPERUSER_ID
from odoo.orm.registry import Registry
from odoo.tools import config

config.parse_config(['-c', r'c:\xampp\htdocs\odoo-19\odoo.conf', '-d', 'odoo19'])

test_data = [
    {
        "name": "Keval pandya",
        "contact_name": "Keval pandya",
        "mobile": "9998045201",
        "created_at": "2026-04-19 09:58:33",
        "company": "Shreemad Family",
        "salesperson": "Megha Trivedi",
        "stage": "Site Visit Done",
        "status": "warm",
        "source": "Walk In",
        "history_notes": [
            {
                "date": "2026-05-03 12:51:18",
                "author": "Megha Trivedi",
                "text": "Visit Scheduled for 2026-05-04: Intested chhe time pass ma"
            },
            {
                "date": "2026-05-03 12:52:37",
                "author": "Megha Trivedi",
                "text": "Visit Done! Outcome: FOLLOW UP REQUIRED | Feedback: Saru lagyu chhe family sathe awana chhe"
            }
        ],
        "pending_activity": {
            "type": "Call",
            "summary": "Follow up post-visit",
            "due_date": "2026-05-19"
        }
    },
    {
        "name": "Subhash panchal",
        "contact_name": "Subhash panchal",
        "mobile": "+917600482171",
        "created_at": "2026-04-26 00:00:00",
        "company": "Shreemad Family",
        "salesperson": "Megha Trivedi",
        "stage": "Contacted / Follow-up",
        "status": "hot",
        "source": "Walk In",
        "history_notes": [
            {
                "date": "2026-04-27 11:46:58",
                "author": "Megha Trivedi",
                "text": "Outbound Call Attempted: Outcome - Busy (Client cut call / busy)"
            }
        ],
        "pending_activity": {
            "type": "Call",
            "summary": "Follow up call",
            "due_date": "2026-08-18"
        }
    },
    {
        "name": "Test Client Megha QA",
        "contact_name": "Test Client Megha QA",
        "mobile": "9876543210",
        "created_at": "2026-08-15 11:51:34",
        "company": "Shreemad Family",
        "salesperson": "Megha Trivedi",
        "stage": "Site Visit Scheduled",
        "status": "hot",
        "source": "Reference",
        "scheduled_visit": {
            "activity_type": "Site Visit",
            "date": "2026-08-16 11:00:00",
            "purpose": "Project site visit demo at Shreemad Family"
        }
    },
    {
        "name": "Kritikajoshi",
        "contact_name": "Kritikajoshi",
        "mobile": "+917357997153",
        "created_at": "2026-04-27 13:52:40",
        "company": "Shreemad Family",
        "salesperson": "Megha Trivedi",
        "stage": "New Lead",
        "status": "hot",
        "source": "WhatsApp"
    },
    {
        "name": "Devendra jani",
        "contact_name": "Devendra jani",
        "mobile": "9974323561",
        "created_at": "2026-04-22 00:00:00",
        "company": "Shreemad Family",
        "salesperson": "Megha Trivedi",
        "stage": "Lost / Not Interested",
        "status": "cold",
        "lost_reason": "Not Interested",
        "source": "Reference"
    }
]


def run_clean_migration():
    registry = Registry('odoo19')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        print("=== 0. Cleaning up old test leads ===")
        mobiles = [d['mobile'] for d in test_data]
        old_leads = env['crm.lead'].with_context(active_test=False).search([('phone', 'in', mobiles)])
        if old_leads:
            print(f"Deleting {len(old_leads)} old test lead(s)...")
            # delete activities and events first
            env['mail.activity'].search([('res_model', '=', 'crm.lead'), ('res_id', 'in', old_leads.ids)]).unlink()
            env['calendar.event'].search([('opportunity_id', 'in', old_leads.ids)]).unlink()
            old_leads.unlink()

        print("=== 1. Setup Company: Shreemad Family ===")
        company = env['res.company'].search([('name', '=', 'Shreemad Family')], limit=1)
        if not company:
            company = env['res.company'].create({'name': 'Shreemad Family', 'currency_id': env.ref('base.INR', raise_if_not_found=False).id or env.company.currency_id.id})
            print(f"Created Company: {company.name}")
        else:
            print(f"Found Company: {company.name}")

        print("=== 2. Setup Salesperson: Megha Trivedi ===")
        user = env['res.users'].search([('name', '=', 'Megha Trivedi')], limit=1)
        if not user:
            user = env['res.users'].create({
                'name': 'Megha Trivedi',
                'login': 'megha.trivedi@diyacrm.com',
                'company_id': company.id,
                'company_ids': [(6, 0, [company.id, env.company.id])],
                'groups_id': [(4, env.ref('sales_team.group_sale_salesman').id)],
            })
            print(f"Created User: {user.name}")
        else:
            print(f"Found User: {user.name}")

        print("=== 3. Setup Pipeline Stages ===")
        stages_def = [
            (1, "New Lead", False, False),
            (2, "Contacted / Follow-up", False, False),
            (3, "Qualified", False, False),
            (4, "Site Visit Scheduled", False, False),
            (5, "Site Visit Done", False, False),
            (6, "Negotiation / Token", False, False),
            (7, "Won / Booked", True, False),
            (8, "Lost / Not Interested", False, True),
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
            stage_map[name] = stg.id

        print("=== 4. Setup UTM Sources ===")
        sources_to_ensure = ["Walk In", "WhatsApp", "Reference", "Social Media", "Direct Call", "AI WhatsApp Agent", "Website"]
        source_map = {}
        for s_name in sources_to_ensure:
            src = env['utm.source'].search([('name', '=', s_name)], limit=1)
            if not src:
                src = env['utm.source'].create({'name': s_name})
            source_map[s_name] = src.id

        print("=== 5. Setup Lost Reason ===")
        lost_reason = env['crm.lost.reason'].search([('name', '=', 'Not Interested')], limit=1)
        if not lost_reason:
            lost_reason = env['crm.lost.reason'].create({'name': 'Not Interested'})

        print("=== 6. Clean Migrating 5 Test Leads (With Hot/Warm/Cold Status & No Stars) ===")
        for data in test_data:
            # Map temperature status directly
            temp_status = data.get('status') or ('hot' if data.get('priority') == '3' else ('warm' if data.get('priority') == '2' else 'cold'))

            lead_vals = {
                'name': data['name'],
                'contact_name': data['contact_name'],
                'phone': data['mobile'],
                'type': 'opportunity',
                'user_id': user.id,
                'company_id': company.id,
                'priority': '0',  # no stars
                'lead_temperature': temp_status,
                'source_id': source_map.get(data.get('source')),
                'stage_id': stage_map.get(data.get('stage')) or stage_map.get('New Lead'),
            }
            if data.get('created_at'):
                lead_vals['create_date'] = data['created_at']

            lead = env['crm.lead'].create(lead_vals)
            print(f"Created Lead: {lead.name} (ID: {lead.id}) | Stage: {data.get('stage')} | Status: {temp_status.upper()}")

            # Handle Lost Stage
            if "Lost" in data.get('stage', ''):
                lead.write({
                    'active': False,
                    'probability': 0,
                    'lost_reason_id': lost_reason.id,
                })

            # Post History Notes into Chatter (mail.message)
            if data.get('history_notes'):
                for note in data['history_notes']:
                    author_partner = user.partner_id.id if note.get('author') == 'Megha Trivedi' else env.user.partner_id.id
                    note_date = note.get('date') or fields.Datetime.now()
                    body_html = f"<div><strong>{note.get('text')}</strong></div>"
                    
                    env['mail.message'].create({
                        'model': 'crm.lead',
                        'res_id': lead.id,
                        'message_type': 'comment',
                        'subtype_id': env.ref('mail.mt_comment').id,
                        'author_id': author_partner,
                        'date': note_date,
                        'body': body_html,
                    })
                    print(f"  -> Added Chatter Note: {note.get('text')[:40]}...")

            # Handle Pending Activity
            if data.get('pending_activity'):
                act_data = data['pending_activity']
                act_type = env['mail.activity.type'].search([('name', '=', 'Call')], limit=1) or env.ref('mail.mail_activity_data_call')
                
                lead.activity_schedule(
                    act_type_xmlid=None,
                    activity_type_id=act_type.id,
                    summary=act_data.get('summary'),
                    date_deadline=act_data.get('due_date'),
                    user_id=user.id,
                )
                print(f"  -> Created Pending Activity: {act_data.get('summary')} (Due: {act_data.get('due_date')})")

            # Handle Scheduled Visit
            if data.get('scheduled_visit'):
                sv = data['scheduled_visit']
                sv_act_type = env['mail.activity.type'].search([('name', '=', 'Site Visit')], limit=1)
                sv_date_str = sv.get('date')  # '2026-08-16 11:00:00'
                sv_deadline = sv_date_str.split(' ')[0]
                
                lead.activity_schedule(
                    act_type_xmlid=None,
                    activity_type_id=sv_act_type.id,
                    summary="Site Visit",
                    date_deadline=sv_deadline,
                    user_id=user.id,
                    note=sv.get('purpose'),
                )
                print(f"  -> Scheduled Site Visit for: {sv_date_str} ({sv.get('purpose')})")

        cr.commit()
        print("\n=== CLEAN MIGRATION COMPLETED SUCCESSFULLY! ===")


if __name__ == '__main__':
    run_clean_migration()

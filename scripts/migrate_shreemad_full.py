# -*- coding: utf-8 -*-
import sys
import os
import json
import datetime
import pytz

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Determine Odoo config path and database
config_path = '/etc/odoo19.conf' if os.path.exists('/etc/odoo19.conf') else r'c:\xampp\htdocs\odoo-19\odoo.conf'
db_name = 'diyacrm' if os.path.exists('/etc/odoo19.conf') else 'odoo19'

# Add Odoo root to path
if os.path.exists('/opt/odoo19/odoo'):
    sys.path.insert(0, '/opt/odoo19/odoo')
else:
    sys.path.insert(0, r"c:\xampp\htdocs\odoo-19")

import odoo
from odoo import api, fields, models, SUPERUSER_ID
from odoo.orm.registry import Registry
from odoo.tools import config

config.parse_config(['-c', config_path, '-d', db_name])


def run_full_migration(json_file_path):
    print(f"=== Reading JSON file from: {json_file_path} ===")
    if not os.path.exists(json_file_path):
        print(f"ERROR: File not found at {json_file_path}")
        return

    with open(json_file_path, 'r', encoding='utf-8') as f:
        leads_data = json.load(f)

    total_leads = len(leads_data)
    print(f"Total Leads to migrate: {total_leads}")

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # 1. Company Setup
        print("\n--- 1. Setting up Companies ---")
        company_map = {}
        unique_companies = list(set([d.get('company', 'Shreemad Family') for d in leads_data if d.get('company')])) or ['Shreemad Family']
        for comp_name in unique_companies:
            comp = env['res.company'].search([('name', '=', comp_name)], limit=1)
            if not comp:
                comp = env['res.company'].create({'name': comp_name})
                print(f"Created Company: {comp_name}")
            else:
                print(f"Found Company: {comp_name}")
            company_map[comp_name] = comp.id

        # 2. Salesperson Setup
        print("\n--- 2. Setting up Salespersons ---")
        user_map = {}
        unique_users = list(set([d.get('salesperson', 'Megha Trivedi') for d in leads_data if d.get('salesperson')]))
        
        main_comp_id = company_map.get('Shreemad Family') or env.company.id
        for u_name in unique_users:
            if not u_name:
                continue
            user = env['res.users'].search([('name', '=', u_name)], limit=1)
            if not user:
                login_clean = u_name.lower().replace(' ', '.') + '@diyacrm.com'
                user_vals = {
                    'name': u_name,
                    'login': login_clean,
                    'company_id': main_comp_id,
                    'company_ids': [(6, 0, list(company_map.values()) + [env.company.id])],
                }
                user = env['res.users'].create(user_vals)
                print(f"Created User: {u_name} ({login_clean})")
            else:
                print(f"Found User: {u_name}")
            user_map[u_name] = user

        # 3. Pipeline Stages Setup
        print("\n--- 3. Setting up Real Estate Stages ---")
        stages_def = [
            (1, "New Lead", ["new", "new lead"], False, False),
            (2, "Contacted / Follow-up", ["contacted", "contacted / follow-up", "followup", "follow up"], False, False),
            (3, "Qualified", ["qualified", "interested"], False, False),
            (4, "Site Visit Scheduled", ["visit scheduled", "site visit scheduled", "visit_scheduled"], False, False),
            (5, "Site Visit Done", ["visit done", "site visit done", "visit_done"], False, False),
            (6, "Negotiation / Token", ["negotiation", "token", "negotiation / token"], False, False),
            (7, "Won / Booked", ["won", "booked", "closed", "won / booked"], True, False),
            (8, "Lost / Not Interested", ["lost", "not interested", "disqualified", "lost / not_interested", "lost / not interested"], False, True),
        ]
        stage_map = {}
        stage_alias_map = {}
        for seq, name, aliases, is_won, is_fold in stages_def:
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
            stage_alias_map[name.lower()] = stg.id
            for al in aliases:
                stage_alias_map[al.lower()] = stg.id

        # 4. UTM Sources Setup
        print("\n--- 4. Setting up UTM Sources ---")
        sources_to_ensure = ["Walk In", "WhatsApp", "Reference", "Social Media", "Direct Call", "AI WhatsApp Agent", "Website", "Hoarding", "Housing"]
        source_map = {}
        for s_name in sources_to_ensure:
            src = env['utm.source'].search([('name', '=', s_name)], limit=1)
            if not src:
                src = env['utm.source'].create({'name': s_name})
            source_map[s_name.lower()] = src.id
            source_map[s_name] = src.id

        # 5. Lost Reason
        lost_reason = env['crm.lost.reason'].search([('name', '=', 'Not Interested')], limit=1)
        if not lost_reason:
            lost_reason = env['crm.lost.reason'].create({'name': 'Not Interested'})

        # Activity Types
        call_act_type = env['mail.activity.type'].search([('name', '=', 'Call')], limit=1) or env.ref('mail.mail_activity_data_call')
        sv_act_type = env['mail.activity.type'].search([('name', '=', 'Site Visit')], limit=1) or env.ref('mail.mail_activity_data_meeting')

        # 6. Migrating Leads in batches
        print("\n--- 5. Starting Batch Lead Migration ---")
        count = 0
        success_count = 0

        for data in leads_data:
            count += 1
            lead_name = data.get('name') or data.get('contact_name') or "Unnamed Client"
            mobile = str(data.get('mobile') or '').strip()
            if not mobile and not lead_name:
                continue

            raw_stage = str(data.get('stage', 'New Lead')).lower().strip()
            stage_id = stage_alias_map.get(raw_stage) or stage_map.get('New Lead')

            raw_source = str(data.get('source', 'Walk In')).strip()
            source_id = source_map.get(raw_source.lower()) or source_map.get('Walk In')

            salesperson_name = data.get('salesperson', 'Megha Trivedi')
            user_obj = user_map.get(salesperson_name) or env.user
            user_id = user_obj.id

            comp_name = data.get('company', 'Shreemad Family')
            comp_id = company_map.get(comp_name) or main_comp_id

            raw_status = str(data.get('status') or '').lower()
            raw_priority = str(data.get('priority') or '')
            if raw_status in ['hot', 'warm', 'cold']:
                lead_temp = raw_status
            elif raw_priority == '3' or 'hot' in raw_priority:
                lead_temp = 'hot'
            elif raw_priority == '2' or 'warm' in raw_priority:
                lead_temp = 'warm'
            else:
                lead_temp = 'cold'

            lead_vals = {
                'name': lead_name,
                'contact_name': data.get('contact_name') or lead_name,
                'phone': mobile,
                'type': 'opportunity',
                'user_id': user_id,
                'company_id': comp_id,
                'priority': '0',
                'lead_temperature': lead_temp,
                'source_id': source_id,
                'stage_id': stage_id,
            }

            if data.get('area'):
                lead_vals['area'] = data.get('area')

            if data.get('created_at'):
                lead_vals['create_date'] = data['created_at']

            lead = env['crm.lead'].create(lead_vals)

            # Handle Lost Stage
            if "lost" in raw_stage or "not interested" in raw_stage or raw_stage == 'disq':
                lead.write({
                    'active': False,
                    'probability': 0,
                    'lost_reason_id': lost_reason.id,
                })

            # History Notes -> mail.message
            history_notes = data.get('history_notes') or []
            for note in history_notes:
                if isinstance(note, dict):
                    note_text = note.get('text') or note.get('body') or ''
                    note_date = note.get('date') or fields.Datetime.now()
                    note_author = note.get('author')
                    author_partner = user_map.get(note_author).partner_id.id if (note_author and note_author in user_map) else user_obj.partner_id.id
                else:
                    note_text = str(note)
                    note_date = fields.Datetime.now()
                    author_partner = user_obj.partner_id.id

                if note_text:
                    body_html = f"<div><strong>{note_text}</strong></div>"
                    env['mail.message'].create({
                        'model': 'crm.lead',
                        'res_id': lead.id,
                        'message_type': 'comment',
                        'subtype_id': env.ref('mail.mt_comment').id,
                        'author_id': author_partner,
                        'date': note_date,
                        'body': body_html,
                    })

            # Pending Follow-up Activity
            pending = data.get('pending_activity')
            if pending and isinstance(pending, dict):
                act_type_name = pending.get('type', 'Call')
                act_type = call_act_type if 'call' in act_type_name.lower() else sv_act_type
                due_date = pending.get('due_date') or str(fields.Date.today())
                lead.activity_schedule(
                    act_type_xmlid=None,
                    activity_type_id=act_type.id,
                    summary=pending.get('summary') or "Follow up",
                    date_deadline=due_date[:10],
                    user_id=user_id,
                )

            # Scheduled Visit
            scheduled = data.get('scheduled_visit')
            if scheduled and isinstance(scheduled, dict):
                sv_date_str = str(scheduled.get('date') or fields.Date.today())
                sv_deadline = sv_date_str.split(' ')[0]
                lead.activity_schedule(
                    act_type_xmlid=None,
                    activity_type_id=sv_act_type.id,
                    summary="Site Visit",
                    date_deadline=sv_deadline,
                    user_id=user_id,
                    note=scheduled.get('purpose') or "Site Visit",
                )

            success_count += 1
            if count % 100 == 0 or count == total_leads:
                cr.commit()
                print(f"Progress: [{count}/{total_leads}] leads processed ({success_count} migrated)...")

        cr.commit()
        print(f"\n=======================================================")
        print(f"🎉 MIGRATION COMPLETE: {success_count}/{total_leads} Leads Successfully Migrated to Odoo!")
        print(f"=======================================================")


if __name__ == '__main__':
    json_path = sys.argv[1] if len(sys.argv) > 1 else '/www/wwwroot/diyacrm/shreemad_clean_odoo_migration.json'
    run_full_migration(json_path)

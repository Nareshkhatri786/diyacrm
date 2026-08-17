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


def parse_datetime_str(date_val):
    if not date_val:
        return fields.Datetime.now()
    if isinstance(date_val, datetime.datetime):
        return date_val.strftime('%Y-%m-%d %H:%M:%S')
    s = str(date_val).replace('T', ' ').replace('Z', '').split('.')[0].strip()
    if len(s) == 10:
        s += ' 00:00:00'
    return s[:19]


def parse_date_only_str(date_val):
    if not date_val:
        return str(fields.Date.today())
    s = str(date_val).split('T')[0].split(' ')[0].strip()
    return s[:10]


def import_shreemad_v2(json_file_path):
    print(f"=== Reading JSON file from: {json_file_path} ===")
    if not os.path.exists(json_file_path):
        print(f"ERROR: File not found at {json_file_path}")
        return

    with open(json_file_path, 'r', encoding='utf-8') as f:
        leads_data = json.load(f)

    total_leads = len(leads_data)
    print(f"Total Records loaded: {total_leads}")

    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # 1. Company Setup (Shreemad Family)
        print("\n--- 1. Setting up Shreemad Family Company ---")
        company = env['res.company'].search([('name', 'ilike', 'Shreemad')], limit=1)
        if not company:
            company = env['res.company'].create({'name': 'Shreemad Family'})
            print("Created Company: Shreemad Family")
        else:
            print(f"Found Company: {company.name} (ID: {company.id})")
        company_id = company.id

        # Ensure Admin user has Shreemad Family as active company
        all_companies = env['res.company'].search([])
        admin_user = env.ref('base.user_admin')
        admin_user.write({
            'company_id': company_id,
            'company_ids': [(6, 0, all_companies.ids)],
        })
        print(f"Admin User set to company: {company.name}")

        # 2. Salespersons Setup
        print("\n--- 2. Setting up Salespersons ---")
        user_map = {}
        unique_users = list(set([d.get('salesperson', 'Megha Trivedi') for d in leads_data if d.get('salesperson')]))
        for u_name in unique_users:
            if not u_name:
                continue
            user = env['res.users'].search([('name', '=ilike', u_name.strip())], limit=1)
            if not user:
                login_clean = u_name.lower().replace(' ', '.') + '@diyacrm.com'
                user = env['res.users'].create({
                    'name': u_name.strip(),
                    'login': login_clean,
                    'company_id': company_id,
                    'company_ids': [(6, 0, all_companies.ids)],
                })
                print(f"Created User: {u_name} ({login_clean})")
            else:
                print(f"Found User: {user.name}")
            user_map[u_name.strip().lower()] = user

        # 3. Pipeline Stages Setup
        print("\n--- 3. Setting up Real Estate Stages ---")
        stages_def = [
            (1, "New Lead", ["new", "new lead"], False, False),
            (2, "Contacted / Follow-up", ["contacted", "contacted / follow-up", "followup", "follow up"], False, False),
            (3, "Qualified", ["qualified", "interested"], False, False),
            (4, "Site Visit Scheduled", ["visit schedule", "visit scheduled", "site visit scheduled", "visit_scheduled"], False, False),
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

        # 4. Sources Setup
        print("\n--- 4. Setting up UTM Sources ---")
        sources_to_ensure = ["Walk In", "WhatsApp", "Reference", "Social Media", "Direct Call", "AI WhatsApp Agent", "Website", "Hoarding", "Housing"]
        source_map = {}
        for s_name in sources_to_ensure:
            src = env['utm.source'].search([('name', '=', s_name)], limit=1)
            if not src:
                src = env['utm.source'].create({'name': s_name})
            source_map[s_name.lower()] = src.id
            source_map[s_name] = src.id

        # 5. Activity Types
        call_act_type = env['mail.activity.type'].search([('name', '=', 'Call')], limit=1) or env.ref('mail.mail_activity_data_call')
        sv_act_type = env['mail.activity.type'].search([('name', '=', 'Site Visit')], limit=1) or env.ref('mail.mail_activity_data_meeting')
        lost_reason = env['crm.lost.reason'].search([('name', '=', 'Not Interested')], limit=1)
        if not lost_reason:
            lost_reason = env['crm.lost.reason'].create({'name': 'Not Interested'})

        # Clean existing leads if any to prevent duplicates on fresh run
        existing_leads = env['crm.lead'].search([('company_id', '=', company_id)])
        if existing_leads:
            print(f"Clearing {len(existing_leads)} existing records in Shreemad Family for clean import...")
            existing_leads.unlink()

        # 6. Import Leads
        print("\n--- 5. Importing Leads with Chatter & Activities ---")
        count = 0
        success_count = 0

        for lead in leads_data:
            count += 1
            lead_name = lead.get('name') or lead.get('contact_name') or "Unnamed Client"
            mobile = str(lead.get('mobile') or '').strip()
            if not mobile and not lead_name:
                continue

            raw_stage = str(lead.get('stage', 'New Lead')).lower().strip()
            stage_id = stage_alias_map.get(raw_stage) or stage_map.get('New Lead')

            raw_source = str(lead.get('source', 'Walk In')).strip()
            source_id = source_map.get(raw_source.lower()) or source_map.get('Walk In')

            salesperson_name = str(lead.get('salesperson') or 'Megha Trivedi').strip().lower()
            user_obj = user_map.get(salesperson_name) or admin_user
            user_id = user_obj.id

            raw_status = str(lead.get('status') or '').lower()
            raw_priority = str(lead.get('priority') or '')
            if raw_status in ['hot', 'warm', 'cold']:
                lead_temp = raw_status
            elif raw_priority == '3' or 'hot' in raw_priority:
                lead_temp = 'hot'
            elif raw_priority == '2' or 'warm' in raw_priority:
                lead_temp = 'warm'
            else:
                lead_temp = 'cold'

            is_active = lead.get('active', True)
            if "lost" in raw_stage or "not interested" in raw_stage or raw_stage == 'disq':
                is_active = False

            lead_vals = {
                'name': lead_name,
                'contact_name': lead.get('contact_name') or lead_name,
                'phone': mobile,
                'email_from': lead.get('email', '') or False,
                'type': 'opportunity',
                'user_id': user_id,
                'company_id': company_id,
                'priority': '0',
                'lead_temperature': lead_temp,
                'source_id': source_id,
                'stage_id': stage_id,
                'active': is_active,
            }

            if lead.get('area'):
                lead_vals['area'] = lead.get('area')

            if lead.get('created_at'):
                lead_vals['create_date'] = parse_datetime_str(lead['created_at'])

            lead_rec = env['crm.lead'].create(lead_vals)

            if not is_active:
                lead_rec.write({
                    'probability': 0,
                    'lost_reason_id': lost_reason.id,
                })

            # Chatter Timeline: calls, notes, past visits
            timeline = lead.get('chatter_timeline') or lead.get('history_notes') or []
            for item in timeline:
                if isinstance(item, dict):
                    content = item.get('content') or item.get('text') or item.get('body') or ''
                    date_val = parse_datetime_str(item.get('date'))
                    author_name = item.get('author')
                    author_partner = user_map.get(author_name.lower()).partner_id.id if (author_name and author_name.lower() in user_map) else user_obj.partner_id.id
                else:
                    content = str(item)
                    date_val = fields.Datetime.now()
                    author_partner = user_obj.partner_id.id

                if content:
                    body_html = f"<div><strong>{content}</strong></div>" if not content.startswith('<') else content
                    env['mail.message'].create({
                        'model': 'crm.lead',
                        'res_id': lead_rec.id,
                        'message_type': 'comment',
                        'subtype_id': env.ref('mail.mt_comment').id,
                        'author_id': author_partner,
                        'date': date_val,
                        'body': body_html,
                    })

            # Pending Follow-up Activity
            activity = lead.get('pending_activity')
            if activity and isinstance(activity, dict) and activity.get('due_date'):
                act_type_name = str(activity.get('type') or 'Call')
                act_type = call_act_type if 'call' in act_type_name.lower() else sv_act_type
                due_date_str = parse_date_only_str(activity['due_date'])
                lead_rec.activity_schedule(
                    act_type_xmlid=None,
                    activity_type_id=act_type.id,
                    summary=activity.get('summary') or "Follow up",
                    date_deadline=due_date_str,
                    user_id=user_id,
                )

            # Scheduled Visit
            scheduled = lead.get('scheduled_visit')
            if scheduled and isinstance(scheduled, dict) and scheduled.get('date'):
                sv_date_str = parse_date_only_str(scheduled.get('date'))
                lead_rec.activity_schedule(
                    act_type_xmlid=None,
                    activity_type_id=sv_act_type.id,
                    summary="Site Visit",
                    date_deadline=sv_date_str,
                    user_id=user_id,
                    note=scheduled.get('purpose') or "Site Visit",
                )

            success_count += 1
            if count % 100 == 0 or count == total_leads:
                cr.commit()
                print(f"Progress: [{count}/{total_leads}] imported...")

        cr.commit()
        print(f"\n=======================================================")
        print(f"🎉 IMPORT COMPLETE: {success_count}/{total_leads} Records Successfully Imported!")
        print(f"=======================================================")


if __name__ == '__main__':
    json_path = sys.argv[1] if len(sys.argv) > 1 else '/www/wwwroot/diyacrm/shreemad_clean_odoo_migration.json'
    import_shreemad_v2(json_path)

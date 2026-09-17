
def format_whatsapp_phone(raw_phone):
    """
    Smart Phone Formatter:
    - Indian Mobile (12 digits starting with 91 & next digit 6/7/8/9, or 10 digits): 
      Returns clean 10-digit number (e.g. 9876543210) for direct SIM calling.
    - International Number:
      Returns with '+' and country code (e.g. +14155552671, +971501234567).
    """
    if not raw_phone:
        return ""
    digits = "".join(filter(str.isdigit, str(raw_phone)))
    
    # 12-digit Indian number starting with 91
    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        return digits[2:]
    # 11-digit Indian number starting with 0
    elif len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
        return digits[1:]
    # Pure 10-digit Indian mobile number
    elif len(digits) == 10 and digits[0] in "6789":
        return digits
    # International number (outside India)
    else:
        return f"+{digits}" if digits else ""

# -*- coding: utf-8 -*-
import json
import logging
import re
import odoo
from odoo import http, fields, SUPERUSER_ID
from odoo.http import request, Response
from odoo.orm.registry import Registry

_logger = logging.getLogger(__name__)

META_VERIFY_TOKEN = "diyacrm_secret_token"

COMPANY_RULES = {
    'the1st': {
        'company_name': 'The 1st Residency',
        'phone_number_ids': ['1305619522636450'],
        'phone_numbers': ['7575863338', '917575863338', '+917575863338'],
        'keywords': ['the 1st', 'the1st', '1st', 'residency', 'the first'],
        'default_salesperson': {
            'name': 'Heer Savaliya',
            'login': 'Heer',
        }
    },
    'royal': {
        'company_name': 'Royal Rudraksha',
        'phone_number_ids': ['1224814500716320', '122101071140010719'],
        'phone_numbers': ['9955343939', '919955343939', '+919955343939'],
        'keywords': ['royal', 'rudraksha'],
        'default_salesperson': {
            'name': 'Krushna Sing',
            'login': 'Krushna',
        }
    },
    'shreemad': {
        'company_name': 'Shreemad Family',
        'phone_number_ids': ['1161115510429761', '1152168267972565'],
        'phone_numbers': ['9327026663', '919327026663', '+919327026663'],
        'keywords': ['shreemad', 'family'],
        'default_salesperson': {
            'name': 'Megha Trivedi',
            'login': 'Megha',
        }
    },
    'devi': {
        'company_name': 'Devi Bungalows',
        'phone_number_ids': ['1265084363352795', '916390071558584'],
        'phone_numbers': ['8849722339', '918849722339', '+918849722339'],
        'keywords': ['devi', 'bungalows', 'bungalow'],
        'default_salesperson': {
            'name': 'Hemant Prajapati',
            'login': 'Hemant',
        }
    },
    'signature': {
        'company_name': 'Signature Properties',
        'phone_number_ids': ['1193758907159434'],
        'phone_numbers': ['7802896663', '917802896663', '+917802896663'],
        'keywords': ['signature'],
        'default_salesperson': {
            'name': 'Megha Trivedi',
            'login': 'Megha',
        }
    }
}


def clean_phone_number(phone_str):
    if not phone_str:
        return ''
    digits = re.sub(r'\D', '', str(phone_str))
    return digits[-10:] if len(digits) >= 10 else digits


class WhatsAppWebhookController(http.Controller):

    @http.route([
        '/api/whatsapp/lead',
        '/webhook/whatsapp',
        '/diyacrm/webhook/whatsapp',
        '/v1/webhook/meta',
        '/api/v1/webhook/meta',
        '/api/inbound-whatsapp-royal.php',
        '/api/inbound-whatsapp-shreemad.php',
        '/api/inbound-whatsapp-devi.php',
        '/api/inbound-whatsapp-the1st.php',
    ], type='http', auth='none', methods=['POST', 'GET'], csrf=False, save_session=False)
    def handle_whatsapp_webhook(self, **kwargs):
        if request.httprequest.method == 'GET':
            mode = kwargs.get('hub.mode') or kwargs.get('mode')
            challenge = kwargs.get('hub.challenge') or kwargs.get('challenge')
            if challenge:
                return Response(str(challenge), status=200, content_type='text/plain')
            return Response(json.dumps({'status': 'online', 'service': 'Diya CRM WhatsApp Webhook Engine', 'version': '4.1'}), status=200, content_type='application/json')

        try:
            raw_body = request.httprequest.get_data() or request.httprequest.data
            if raw_body:
                try:
                    payload = json.loads(raw_body.decode('utf-8'))
                except Exception:
                    payload = kwargs
            else:
                payload = kwargs

            db_name = request.db or request.httprequest.headers.get('X-Odoo-Db') or 'diyacrm'
            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, SUPERUSER_ID, {})

                if 'entry' in payload and isinstance(payload['entry'], list):
                    results = self._parse_and_process_meta_payload(env, payload)
                    cr.commit()
                    return Response(json.dumps({'status': 'success', 'processed': len(results), 'details': results}), status=200, content_type='application/json')

                payload['_url_path'] = request.httprequest.path
                payload['_url_account'] = kwargs.get('account')
                result = self._process_inbound_lead(env, payload)
                cr.commit()

                status_code = 200 if result.get('status') in ['success', 'ignored'] else 400
                return Response(json.dumps(result), status=status_code, content_type='application/json')

        except Exception as e:
            _logger.exception("Diya CRM Webhook Ingestion Exception: %s", str(e))
            return Response(json.dumps({'status': 'error', 'message': str(e)}), status=200, content_type='application/json')

    def _parse_and_process_meta_payload(self, env, payload):
        results = []
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                metadata = value.get('metadata', {})
                phone_number_id = metadata.get('phone_number_id', '')
                display_phone_number = metadata.get('display_phone_number', '')

                if 'statuses' in value and not value.get('messages'):
                    continue

                contacts_map = {}
                for c in value.get('contacts', []):
                    wa_id = c.get('wa_id')
                    profile_name = c.get('profile', {}).get('name') or "WhatsApp User"
                    if wa_id:
                        contacts_map[str(wa_id)] = profile_name

                messages = value.get('messages', [])
                for msg in messages:
                    from_number = str(msg.get('from', '')).strip()
                    if not from_number:
                        continue

                    msg_type = msg.get('type', 'text')
                    text_body = ""
                    if msg_type == 'text':
                        text_body = msg.get('text', {}).get('body', '')
                    elif msg_type == 'interactive':
                        interactive = msg.get('interactive', {})
                        text_body = interactive.get('button_reply', {}).get('title') or interactive.get('list_reply', {}).get('title') or 'Interactive Selection'
                    elif msg_type == 'button':
                        text_body = msg.get('button', {}).get('text', '')
                    elif msg_type in ['image', 'document', 'video', 'audio']:
                        caption = msg.get(msg_type, {}).get('caption', '')
                        text_body = f"Sent a {msg_type}: {caption}" if caption else f"Sent a {msg_type}"
                    elif msg_type == 'location':
                        loc = msg.get('location', {})
                        text_body = f"Shared Location: Lat {loc.get('latitude')}, Long {loc.get('longitude')}"
                    else:
                        text_body = f"WhatsApp Message ({msg_type})"

                    customer_name = contacts_map.get(from_number) or f"Client ({from_number[-10:]})"

                    lead_payload = {
                        'recipientPhoneNumberId': phone_number_id,
                        'display_phone_number': display_phone_number,
                        'name': customer_name,
                        'phone': format_whatsapp_phone(from_number),
                        'message': text_body,
                        'source': 'AI WhatsApp Agent',
                    }

                    res = self._process_inbound_lead(env, lead_payload)
                    results.append(res)
        return results

    def _determine_company_and_rule(self, env, data):
        url_path = str(data.get('_url_path') or '').lower()
        account_param = str(data.get('_url_account') or data.get('account') or '').lower()
        phone_number_id = str(
            data.get('recipientPhoneNumberId') or
            data.get('phone_number_id') or
            data.get('metadata', {}).get('phone_number_id') or ''
        ).strip()
        
        display_phone = str(
            data.get('display_phone_number') or
            data.get('business_number') or
            data.get('metadata', {}).get('display_phone_number') or ''
        ).replace('+', '').replace(' ', '')

        project_str = str(data.get('project') or data.get('company') or data.get('project_name') or '').strip().lower()

        matched_key = None

        if 'the1st' in url_path or '1st' in url_path or 'the1st' in account_param or '1st' in account_param:
            matched_key = 'the1st'
        elif 'royal' in url_path or 'royal' in account_param:
            matched_key = 'royal'
        elif 'shreemad' in url_path or 'shreemad' in account_param:
            matched_key = 'shreemad'
        elif 'devi' in url_path or 'devi' in account_param:
            matched_key = 'devi'
        elif 'signature' in url_path or 'signature' in account_param:
            matched_key = 'signature'

        if not matched_key and phone_number_id:
            for k, rule in COMPANY_RULES.items():
                if phone_number_id in rule['phone_number_ids']:
                    matched_key = k
                    break

        if not matched_key and display_phone:
            for k, rule in COMPANY_RULES.items():
                if any(num.replace('+', '') in display_phone for num in rule['phone_numbers']):
                    matched_key = k
                    break

        if not matched_key and project_str:
            for k, rule in COMPANY_RULES.items():
                if any(kw in project_str for kw in rule['keywords']):
                    matched_key = k
                    break

        if not matched_key:
            matched_key = 'royal'

        rule = COMPANY_RULES[matched_key]
        company = env['res.company'].search([('name', 'ilike', rule['company_name'])], limit=1)
        if not company:
            company = env['res.company'].create({'name': rule['company_name']})

        return company, rule

    def _get_or_create_salesperson(self, env, company, rule, direct_param=None):
        target_name = direct_param or rule['default_salesperson']['name']
        target_login = rule['default_salesperson']['login'] if not direct_param else target_name.lower().replace(' ', '.') + '@diyacrm.com'

        user = env['res.users'].search([('name', '=ilike', target_name.strip())], limit=1)
        if not user and target_login:
            user = env['res.users'].search([('login', '=ilike', target_login.strip())], limit=1)

        all_companies = env['res.company'].search([])

        if not user:
            user = env['res.users'].create({
                'name': target_name.strip(),
                'login': target_login,
                'company_id': company.id,
                'company_ids': [(6, 0, all_companies.ids)],
            })
        else:
            if company.id not in user.company_ids.ids:
                user.write({'company_ids': [(4, company.id)]})

        return user

    def _process_inbound_lead(self, env, data):
        _logger.info("Diya CRM Webhook Payload Processing: %s", data)

        raw_phone = str(data.get('phone') or data.get('mobile') or data.get('wa_number') or data.get('from') or '').strip()
        message = data.get('message') or data.get('last_message') or data.get('chat_history') or data.get('body') or ''
        clean_mobile_10 = clean_phone_number(raw_phone)

        if not clean_mobile_10 and not raw_phone and not message:
            return {'status': 'ignored', 'message': 'Empty webhook payload'}

        company, rule = self._determine_company_and_rule(env, data)
        company_id = company.id
        company_name = company.name

        name = data.get('name') or data.get('customer_name') or data.get('contact_name')
        email = data.get('email') or False
        area = data.get('area') or False

        if not name:
            name = f"WhatsApp Lead ({clean_mobile_10})" if clean_mobile_10 else "New WhatsApp Lead"

        salesperson_param = data.get('salesperson') or data.get('user') or data.get('assigned_to')
        assigned_user = self._get_or_create_salesperson(env, company, rule, salesperson_param)

        raw_source = str(data.get('source') or 'AI WhatsApp Agent').strip()
        utm_source = env['utm.source'].search([('name', '=ilike', raw_source)], limit=1) or env['utm.source'].search([('name', '=ilike', 'AI WhatsApp Agent')], limit=1) or env['utm.source'].search([('name', '=ilike', 'WhatsApp')], limit=1)
        if not utm_source:
            utm_source = env['utm.source'].create({'name': 'AI WhatsApp Agent'})

        raw_status = str(data.get('status') or 'warm').lower().strip()
        lead_temp = raw_status if raw_status in ['hot', 'warm', 'cold'] else 'warm'

        stage_new = env['crm.stage'].search([('name', '=ilike', 'New Lead')], limit=1) or env['crm.stage'].search([], order='sequence asc', limit=1)
        call_act_type = env['mail.activity.type'].search([('name', '=', 'Call')], limit=1) or env.ref('mail.mail_activity_data_call')

        existing_lead = None
        if clean_mobile_10:
            existing_lead = env['crm.lead'].with_context(active_test=False).search([
                ('company_id', '=', company_id),
                ('phone', 'like', clean_mobile_10)
            ], order='id desc', limit=1)

        lead_action = "created"

        if existing_lead and existing_lead.active:
            lead = existing_lead
            lead_action = "updated_active"
            if message:
                body_html = f"""
                <div style="background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 10px; border-radius: 4px;">
                    <p style="margin: 0 0 5px 0; color: #166534; font-weight: bold;">📱 New WhatsApp Message:</p>
                    <div style="color: #1f2937; white-space: pre-wrap;">{message}</div>
                </div>
                """
                env['mail.message'].create({
                    'model': 'crm.lead',
                    'res_id': lead.id,
                    'message_type': 'comment',
                    'subtype_id': env.ref('mail.mt_comment').id,
                    'author_id': lead.user_id.partner_id.id if lead.user_id else assigned_user.partner_id.id,
                    'body': body_html,
                })

            lead.activity_schedule(
                act_type_xmlid=None,
                activity_type_id=call_act_type.id,
                summary="Inbound WhatsApp message received",
                date_deadline=fields.Date.today(),
                user_id=lead.user_id.id if lead.user_id else assigned_user.id,
                note="Client sent a new message via WhatsApp. Please check and reply."
            )

            return {'status': 'success', 'action': lead_action, 'lead_id': lead.id, 'lead_name': lead.name, 'phone': lead.phone, 'project': company_name, 'assigned_to': lead.user_id.name if lead.user_id else assigned_user.name}

        elif existing_lead and not existing_lead.active:
            lead = existing_lead
            lead_action = "reopened_from_lost"
            target_user = lead.user_id if lead.user_id else assigned_user
            lead.write({
                'active': True,
                'stage_id': stage_new.id if stage_new else 5,
                'probability': False,
                'lost_reason_id': False,
                'user_id': target_user.id,
                'lead_temperature': 'hot',
            })

            if message:
                body_html = f"""
                <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 10px; border-radius: 4px; margin-bottom: 6px;">
                    <div style="color: #991b1b; font-weight: 800; font-size: 13px;">🔥 RE-ENQUIRY FROM LOST CLIENT!</div>
                    <div style="font-size: 11px; color: #b91c1c; margin-bottom: 6px;">Lead has been auto-revived from Lost to Active Pipeline.</div>
                    <p style="margin: 0 0 5px 0; color: #166534; font-weight: bold;">📱 WhatsApp Message:</p>
                    <div style="color: #1f2937; white-space: pre-wrap;">{message}</div>
                </div>
                """
                env['mail.message'].create({
                    'model': 'crm.lead',
                    'res_id': lead.id,
                    'message_type': 'comment',
                    'subtype_id': env.ref('mail.mt_comment').id,
                    'author_id': target_user.partner_id.id,
                    'body': body_html,
                })

            lead.activity_schedule(
                act_type_xmlid=None,
                activity_type_id=call_act_type.id,
                summary="🔥 URGENT RE-ENQUIRY: Lost Client Sent WhatsApp!",
                date_deadline=fields.Date.today(),
                user_id=target_user.id,
                note=f"Client sent WhatsApp message: '{message}'. Please call back immediately!"
            )

            return {'status': 'success', 'action': lead_action, 'lead_id': lead.id, 'lead_name': lead.name, 'phone': lead.phone, 'project': company_name, 'assigned_to': target_user.name}

        else:
            lead_vals = {
                'name': name,
                'contact_name': name,
                'phone': format_whatsapp_phone(raw_phone),
                'email_from': email,
                'type': 'opportunity',
                'company_id': company_id,
                'user_id': assigned_user.id,
                'stage_id': stage_new.id if stage_new else False,
                'source_id': utm_source.id if utm_source else False,
                'lead_temperature': lead_temp,
                'priority': '0',
            }

            if area:
                valid_areas = [k for k, v in env['crm.lead']._fields['area'].selection]
                area_key = area.lower().replace(' ', '_')
                if area_key in valid_areas:
                    lead_vals['area'] = area_key
                elif area in valid_areas:
                    lead_vals['area'] = area

            lead = env['crm.lead'].create(lead_vals)

            if message:
                body_html = f"""
                <div style="background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 10px; border-radius: 4px;">
                    <p style="margin: 0 0 5px 0; color: #166534; font-weight: bold;">📱 Inbound WhatsApp Message:</p>
                    <div style="color: #1f2937; white-space: pre-wrap;">{message}</div>
                </div>
                """
                env['mail.message'].create({
                    'model': 'crm.lead',
                    'res_id': lead.id,
                    'message_type': 'comment',
                    'subtype_id': env.ref('mail.mt_comment').id,
                    'author_id': assigned_user.partner_id.id,
                    'body': body_html,
                })

            lead.activity_schedule(
                act_type_xmlid=None,
                activity_type_id=call_act_type.id,
                summary="New WhatsApp Lead - Call & Qualify",
                date_deadline=fields.Date.today(),
                user_id=assigned_user.id,
                note="Lead received via WhatsApp bot. Please call immediately."
            )

            return {'status': 'success', 'action': lead_action, 'lead_id': lead.id, 'lead_name': lead.name, 'phone': lead.phone, 'project': company_name, 'assigned_to': assigned_user.name}

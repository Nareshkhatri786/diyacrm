# -*- coding: utf-8 -*-
import json
import logging
import re
from odoo import http, fields, SUPERUSER_ID
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# Default Meta Webhook Verify Token
META_VERIFY_TOKEN = "diyacrm_secret_token"

# Phone Number IDs & Keywords Mapping to Companies & Dedicated Users
COMPANY_RULES = {
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
            'login': 'megha.trivedi@diyacrm.com',
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
            'login': 'megha.trivedi@diyacrm.com',
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
    ], type='http', auth='public', methods=['POST', 'GET'], csrf=False)
    def handle_whatsapp_webhook(self, **kwargs):
        # 1. META WEBHOOK VERIFICATION (GET REQUEST)
        if request.httprequest.method == 'GET':
            mode = kwargs.get('hub.mode') or kwargs.get('mode')
            token = kwargs.get('hub.verify_token') or kwargs.get('verify_token') or kwargs.get('token')
            challenge = kwargs.get('hub.challenge') or kwargs.get('challenge')

            if mode and challenge:
                _logger.info("Meta Webhook Verification: mode=%s, token=%s", mode, token)
                return Response(str(challenge), status=200, content_type='text/plain')

            if challenge:
                return Response(str(challenge), status=200, content_type='text/plain')

            return Response(
                json.dumps({
                    'status': 'online',
                    'service': 'Diya CRM Meta Cloud API & WhatsApp Webhook Engine',
                    'version': '3.0',
                    'verify_token': META_VERIFY_TOKEN
                }),
                status=200,
                content_type='application/json'
            )

        # 2. INBOUND WEBHOOK DATA PROCESSING (POST REQUEST)
        try:
            raw_data = request.httprequest.data
            if raw_data:
                try:
                    payload = json.loads(raw_data.decode('utf-8'))
                except Exception:
                    payload = kwargs
            else:
                payload = kwargs

            env = request.env(user=SUPERUSER_ID)

            # Check if Meta WhatsApp Cloud API Payload
            if 'entry' in payload and isinstance(payload['entry'], list):
                results = self._parse_and_process_meta_payload(env, payload)
                return Response(json.dumps({'status': 'success', 'processed': len(results), 'details': results}), status=200, content_type='application/json')

            # Direct JSON Payload
            payload['_url_path'] = request.httprequest.path
            payload['_url_account'] = kwargs.get('account')
            result = self._process_inbound_lead(env, payload)
            status_code = 200 if result.get('status') in ['success', 'ignored'] else 400
            return Response(json.dumps(result), status=status_code, content_type='application/json')
        except Exception as e:
            _logger.exception("Diya CRM Webhook Error: %s", str(e))
            return Response(json.dumps({'status': 'error', 'message': str(e)}), status=500, content_type='application/json')

    def _parse_and_process_meta_payload(self, env, payload):
        results = []
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                metadata = value.get('metadata', {})
                phone_number_id = metadata.get('phone_number_id', '')
                display_phone_number = metadata.get('display_phone_number', '')

                # Ignore status delivery receipts (sent / delivered / read updates)
                if 'statuses' in value and not value.get('messages'):
                    _logger.info("Ignoring Meta status delivery receipt (statuses update)")
                    continue

                # Contacts mapping (Name & wa_id)
                contacts_map = {}
                for c in value.get('contacts', []):
                    wa_id = c.get('wa_id')
                    profile_name = c.get('profile', {}).get('name') or "WhatsApp User"
                    if wa_id:
                        contacts_map[wa_id] = profile_name

                # Messages
                messages = value.get('messages', [])
                if not messages:
                    continue

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
                        'phone': f"+{from_number}" if not from_number.startswith('+') else from_number,
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

        if 'royal' in url_path or 'royal' in account_param:
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
            _logger.info("Auto-created dedicated Salesperson: %s (%s)", user.name, user.login)
        else:
            if company.id not in user.company_ids.ids:
                user.write({
                    'company_ids': [(4, company.id)],
                })

        return user

    def _process_inbound_lead(self, env, data):
        _logger.info("Diya CRM Webhook Payload Processing: %s", data)

        raw_phone = str(data.get('phone') or data.get('mobile') or data.get('wa_number') or data.get('from') or '').strip()
        message = data.get('message') or data.get('last_message') or data.get('chat_history') or data.get('body') or ''
        clean_mobile_10 = clean_phone_number(raw_phone)

        # Ignore empty test pings with no phone number and no message
        if not clean_mobile_10 and not raw_phone and not message:
            _logger.info("Ignoring empty webhook payload with no phone or message.")
            return {
                'status': 'ignored',
                'message': 'Empty webhook payload with no phone number or message'
            }

        # 1. Determine Company & Rule
        company, rule = self._determine_company_and_rule(env, data)
        company_id = company.id
        company_name = company.name

        # 2. Extract Lead Info
        name = data.get('name') or data.get('customer_name') or data.get('contact_name')
        email = data.get('email') or False
        area = data.get('area') or False

        if not name:
            name = f"WhatsApp Lead ({clean_mobile_10})" if clean_mobile_10 else "New WhatsApp Lead"

        # 3. Determine Dedicated Salesperson
        salesperson_param = data.get('salesperson') or data.get('user') or data.get('assigned_to')
        assigned_user = self._get_or_create_salesperson(env, company, rule, salesperson_param)

        # 4. Source & Status
        raw_source = str(data.get('source') or 'AI WhatsApp Agent').strip()
        utm_source = env['utm.source'].search([('name', '=ilike', raw_source)], limit=1) or env['utm.source'].search([('name', '=ilike', 'AI WhatsApp Agent')], limit=1) or env['utm.source'].search([('name', '=ilike', 'WhatsApp')], limit=1)
        if not utm_source:
            utm_source = env['utm.source'].create({'name': 'AI WhatsApp Agent'})

        raw_status = str(data.get('status') or 'warm').lower().strip()
        lead_temp = raw_status if raw_status in ['hot', 'warm', 'cold'] else 'warm'

        stage_new = env['crm.stage'].search([('name', '=ilike', 'New Lead')], limit=1) or env['crm.stage'].search([], order='sequence asc', limit=1)
        call_act_type = env['mail.activity.type'].search([('name', '=', 'Call')], limit=1) or env.ref('mail.mail_activity_data_call')

        # 5. Check Existing Lead ONLY in THIS Company
        existing_lead = None
        if clean_mobile_10:
            existing_lead = env['crm.lead'].with_context(active_test=False).search([
                ('company_id', '=', company_id),
                ('phone', 'like', clean_mobile_10)
            ], order='id desc', limit=1)

        lead_action = "created"

        # CASE A: Lead Exists & is ACTIVE
        if existing_lead and existing_lead.active:
            lead = existing_lead
            lead_action = "updated_active"
            _logger.info("Found ACTIVE existing lead ID %s in %s. Updating timeline...", lead.id, company_name)
            
            if message:
                body_html = f"""
                <div style="background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 10px; border-radius: 4px;">
                    <p style="margin: 0 0 5px 0; color: #166534; font-weight: bold;">
                        📱 New WhatsApp Message:
                    </p>
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

            return {
                'status': 'success',
                'action': lead_action,
                'lead_id': lead.id,
                'lead_name': lead.name,
                'phone': lead.phone,
                'project': company_name,
                'assigned_to': lead.user_id.name if lead.user_id else assigned_user.name,
                'stage': lead.stage_id.name if lead.stage_id else 'New Lead',
                'status_temperature': lead.lead_temperature,
                'message': 'Existing active lead updated with new WhatsApp message'
            }

        # CASE B: Lead Exists & is LOST -> RE-OPEN TO NEW LEAD
        elif existing_lead and not existing_lead.active:
            lead = existing_lead
            lead_action = "reopened_from_lost"
            _logger.info("Found LOST lead ID %s in %s. RE-OPENING to New Lead...", lead.id, company_name)

            lead.write({
                'active': True,
                'stage_id': stage_new.id if stage_new else False,
                'probability': False,
                'lost_reason_id': False,
                'user_id': assigned_user.id,
                'lead_temperature': lead_temp,
            })

            reopen_body = f"""
            <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 10px; border-radius: 4px; margin-bottom: 8px;">
                <p style="margin: 0; color: #1e40af; font-weight: bold;">
                    🔄 Lead RE-OPENED from Lost! (New WhatsApp Inquiry Received)
                </p>
                <p style="margin: 4px 0 0 0; color: #1e3a8a; font-size: 12px;">
                    Assigned to: <strong>{assigned_user.name}</strong>
                </p>
            </div>
            """
            if message:
                reopen_body += f"""
                <div style="background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 10px; border-radius: 4px;">
                    <p style="margin: 0 0 5px 0; color: #166534; font-weight: bold;">📱 WhatsApp Message:</p>
                    <div style="color: #1f2937; white-space: pre-wrap;">{message}</div>
                </div>
                """

            env['mail.message'].create({
                'model': 'crm.lead',
                'res_id': lead.id,
                'message_type': 'comment',
                'subtype_id': env.ref('mail.mt_comment').id,
                'author_id': assigned_user.partner_id.id,
                'body': reopen_body,
            })

            lead.activity_schedule(
                act_type_xmlid=None,
                activity_type_id=call_act_type.id,
                summary="Re-opened Lead - Call Immediately",
                date_deadline=fields.Date.today(),
                user_id=assigned_user.id,
                note="Lost client has sent a new WhatsApp inquiry. Please call back immediately."
            )

            return {
                'status': 'success',
                'action': lead_action,
                'lead_id': lead.id,
                'lead_name': lead.name,
                'phone': lead.phone,
                'project': company_name,
                'assigned_to': assigned_user.name,
                'stage': stage_new.name if stage_new else 'New Lead',
                'status_temperature': lead.lead_temperature,
                'message': 'Lost lead successfully re-opened and assigned to dedicated salesperson'
            }

        # CASE C: Brand NEW Lead Creation
        else:
            lead_vals = {
                'name': name,
                'contact_name': name,
                'phone': raw_phone,
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
                    <p style="margin: 0 0 5px 0; color: #166534; font-weight: bold;">
                        📱 Inbound WhatsApp Message:
                    </p>
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

            return {
                'status': 'success',
                'action': lead_action,
                'lead_id': lead.id,
                'lead_name': lead.name,
                'phone': lead.phone,
                'project': company_name,
                'assigned_to': assigned_user.name,
                'stage': stage_new.name if stage_new else 'New Lead',
                'status_temperature': lead.lead_temperature,
                'message': 'New lead created and assigned to dedicated salesperson'
            }

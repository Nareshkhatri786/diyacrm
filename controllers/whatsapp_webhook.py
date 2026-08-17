# -*- coding: utf-8 -*-
import json
import logging
from odoo import http, fields, SUPERUSER_ID
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class WhatsAppWebhookController(http.Controller):

    @http.route([
        '/api/whatsapp/lead',
        '/webhook/whatsapp',
        '/diyacrm/webhook/whatsapp'
    ], type='http', auth='public', methods=['POST', 'GET'], csrf=False)
    def handle_whatsapp_webhook(self, **kwargs):
        """
        Universal Webhook Endpoint for WhatsApp / Meta / Wati / AiSensy / Chatbot integration.
        GET: Webhook verification / Health check ping
        POST: Inbound lead creation with project-wise distribution
        """
        if request.httprequest.method == 'GET':
            hub_challenge = kwargs.get('hub.challenge') or kwargs.get('challenge')
            if hub_challenge:
                return Response(hub_challenge, status=200, content_type='text/plain')
            return Response(
                json.dumps({
                    'status': 'online',
                    'service': 'Diya CRM WhatsApp Webhook Engine',
                    'version': '1.0'
                }),
                status=200,
                content_type='application/json'
            )

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
            result = self._process_inbound_lead(env, payload)
            status_code = 200 if result.get('status') == 'success' else 400
            return Response(json.dumps(result), status=status_code, content_type='application/json')
        except Exception as e:
            _logger.exception("Diya CRM Webhook Error: %s", str(e))
            return Response(json.dumps({'status': 'error', 'message': str(e)}), status=500, content_type='application/json')

    def _process_inbound_lead(self, env, data):
        _logger.info("Received Inbound WhatsApp Lead: %s", data)

        # 1. Determine Project / Company
        project_param = str(data.get('project') or data.get('company') or data.get('project_name') or '').strip().lower()
        company = None
        if 'royal' in project_param or 'rudraksha' in project_param:
            company = env['res.company'].search([('name', 'ilike', 'Royal Rudraksha')], limit=1) or env['res.company'].search([('name', 'ilike', 'Royal')], limit=1)
        elif 'shreemad' in project_param or 'family' in project_param:
            company = env['res.company'].search([('name', 'ilike', 'Shreemad Family')], limit=1) or env['res.company'].search([('name', 'ilike', 'Shreemad')], limit=1)
        elif project_param:
            company = env['res.company'].search([('name', 'ilike', project_param)], limit=1)

        if not company:
            company = env['res.company'].search([('name', 'ilike', 'Royal Rudraksha')], limit=1) or env['res.company'].search([('name', 'ilike', 'Shreemad')], limit=1) or env['res.company'].search([], limit=1)

        company_id = company.id
        company_name = company.name

        # 2. Extract Lead Info
        name = data.get('name') or data.get('customer_name') or data.get('contact_name')
        mobile = str(data.get('phone') or data.get('mobile') or data.get('wa_number') or '').strip()
        email = data.get('email') or False
        area = data.get('area') or False
        message = data.get('message') or data.get('last_message') or data.get('chat_history') or ''

        if not name:
            name = f"WhatsApp Lead ({mobile})" if mobile else "New WhatsApp Lead"

        # 3. Source Setup
        raw_source = str(data.get('source') or 'AI WhatsApp Agent').strip()
        utm_source = env['utm.source'].search([('name', '=ilike', raw_source)], limit=1)
        if not utm_source:
            utm_source = env['utm.source'].search([('name', '=ilike', 'AI WhatsApp Agent')], limit=1) or env['utm.source'].search([('name', '=ilike', 'WhatsApp')], limit=1)
        if not utm_source:
            utm_source = env['utm.source'].create({'name': 'AI WhatsApp Agent'})

        # 4. Status / Temperature
        raw_status = str(data.get('status') or 'warm').lower().strip()
        lead_temp = 'warm'
        if raw_status in ['hot', 'warm', 'cold']:
            lead_temp = raw_status

        # 5. Smart User Distribution (Project-Wise Round Robin / Direct Assign)
        salesperson_param = str(data.get('salesperson') or data.get('user') or data.get('assigned_to') or '').strip()
        assigned_user = None

        if salesperson_param:
            assigned_user = env['res.users'].search([
                ('name', '=ilike', salesperson_param),
                ('company_ids', 'in', [company_id])
            ], limit=1)
            if not assigned_user:
                assigned_user = env['res.users'].search([('name', '=ilike', salesperson_param)], limit=1)

        if not assigned_user:
            # Round-Robin Distribution among active users assigned to this project
            project_users = env['res.users'].search([
                ('company_ids', 'in', [company_id]),
                ('share', '=', False),
                ('id', '!=', SUPERUSER_ID)
            ], order='id asc')

            sales_reps = [u for u in project_users if u.login.lower() not in ['admin', 'odoobot', 'bot']]
            candidate_users = sales_reps if sales_reps else project_users

            if candidate_users:
                param_key = f"diyacrm.round_robin_last_uid_{company_id}"
                last_uid_str = env['ir.config_parameter'].sudo().get_param(param_key)
                try:
                    last_uid = int(last_uid_str) if last_uid_str else 0
                except ValueError:
                    last_uid = 0

                user_ids = [u.id for u in candidate_users]
                if last_uid in user_ids:
                    current_idx = user_ids.index(last_uid)
                    next_idx = (current_idx + 1) % len(user_ids)
                else:
                    next_idx = 0

                assigned_user = candidate_users[next_idx]
                env['ir.config_parameter'].sudo().set_param(param_key, str(assigned_user.id))
            else:
                assigned_user = env.ref('base.user_admin')

        # 6. Pipeline Stage (New Lead)
        stage = env['crm.stage'].search([('name', '=ilike', 'New Lead')], limit=1) or env['crm.stage'].search([], order='sequence asc', limit=1)

        # 7. Create CRM Lead
        lead_vals = {
            'name': name,
            'contact_name': name,
            'phone': mobile,
            'email_from': email,
            'type': 'opportunity',
            'company_id': company_id,
            'user_id': assigned_user.id,
            'stage_id': stage.id if stage else False,
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

        # 8. Post WhatsApp Conversation into Chatter
        if message:
            body_html = f"""
            <div style="background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 10px; border-radius: 4px; font-family: sans-serif;">
                <p style="margin: 0 0 5px 0; color: #166534; font-weight: bold;">
                    📱 Inbound WhatsApp Message / Chat Summary:
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

        # 9. Schedule Follow-up Call Activity for Today
        call_act_type = env['mail.activity.type'].search([('name', '=', 'Call')], limit=1) or env.ref('mail.mail_activity_data_call')
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
            'lead_id': lead.id,
            'lead_name': lead.name,
            'phone': lead.phone,
            'project': company_name,
            'assigned_to': assigned_user.name,
            'assigned_user_id': assigned_user.id,
            'stage': stage.name if stage else 'New Lead',
            'status_temperature': lead.lead_temperature,
            'message': 'Lead created and distributed successfully'
        }

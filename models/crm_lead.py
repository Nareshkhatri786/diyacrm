# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import datetime
import pytz


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    area = fields.Selection([
        ('hanspura', 'Hanspura'),
        ('nikol', 'Nikol'),
        ('vatva_lambha', 'Vatva / Lambha'),
        ('naroda_nava_naroda', 'Naroda / Nava Naroda'),
        ('vastral', 'Vastral'),
        ('odhav', 'Odhav'),
        ('narol', 'Narol'),
        ('isanpur', 'Isanpur'),
        ('ghodasar', 'Ghodasar'),
        ('kathwada', 'Kathwada'),
        ('hathijan', 'Hathijan'),
        ('ctm_ramol', 'CTM / Ramol'),
        ('aslali', 'Aslali'),
        ('maninagar', 'Maninagar'),
        ('other_ahmedabad', 'Other Area (Ahmedabad)'),
        ('outside_ahmedabad', 'Outside Ahmedabad'),
    ], string="Area", tracking=True)

    lead_temperature = fields.Selection([
        ('hot', '🔥 Hot'),
        ('warm', '⛅ Warm'),
        ('cold', '❄️ Cold'),
    ], string="Status", default='warm', tracking=True)

    last_call_outcome = fields.Selection([
        ('answered', 'Answered'),
        ('no_answer', 'No answer'),
        ('busy', 'Busy'),
        ('switched_off', 'Switched off'),
    ], string="Last Call Outcome", tracking=True)

    @api.depends('calendar_event_ids.start')
    def _compute_meeting_display(self):
        now = fields.Datetime.now()
        meeting_data = self.env['calendar.event'].sudo()._read_group([
            ('opportunity_id', 'in', self.ids),
        ], ['opportunity_id'], ['start:array_agg', 'start:max'])
        mapped_data = {
            lead: {
                'last_meeting_date': last_meeting_date,
                'next_meeting_date': min([dt for dt in meeting_start_dates if dt > now] or [False]),
            } for lead, meeting_start_dates, last_meeting_date in meeting_data
        }
        for lead in self:
            lead_meeting_info = mapped_data.get(lead)
            if not lead_meeting_info:
                lead.meeting_display_date = False
                lead.meeting_display_label = _('No Site Visit')
            elif lead_meeting_info['next_meeting_date']:
                lead.meeting_display_date = fields.Datetime.context_timestamp(lead, lead_meeting_info['next_meeting_date'])
                lead.meeting_display_label = _('Next Site Visit')
            else:
                lead.meeting_display_date = fields.Datetime.context_timestamp(lead, lead_meeting_info['last_meeting_date'])
                lead.meeting_display_label = _('Last Site Visit')

    @api.model
    def _register_hook(self):
        super()._register_hook()
        try:
            # 1. Deactivate Email & Document
            email_act = self.env.ref('mail.mail_activity_data_email', raise_if_not_found=False)
            if email_act and email_act.active:
                email_act.sudo().write({'active': False})

            doc_act = self.env.ref('mail.mail_activity_data_upload_document', raise_if_not_found=False)
            if doc_act and doc_act.active:
                doc_act.sudo().write({'active': False})

            # 2. 1st: Call (sequence 1)
            call_act = self.env.ref('mail.mail_activity_data_call', raise_if_not_found=False)
            if call_act:
                call_act.sudo().write({'sequence': 1, 'active': True})

            # 3. 2nd: Meeting -> Site Visit (sequence 2, category='default')
            meeting_act = self.env.ref('mail.mail_activity_data_meeting', raise_if_not_found=False)
            if meeting_act:
                meeting_act.sudo().write({
                    'name': 'Site Visit',
                    'summary': 'Site Visit',
                    'icon': 'fa-building',
                    'category': 'default',
                    'delay_count': 0,
                    'sequence': 2,
                    'active': True,
                })

            # 4. 3rd: WhatsApp (sequence 3)
            whatsapp_act = self.env['mail.activity.type'].sudo().search([('name', '=', 'WhatsApp')], limit=1)
            if not whatsapp_act:
                whatsapp_act = self.env['mail.activity.type'].sudo().create({
                    'name': 'WhatsApp',
                    'summary': 'WhatsApp',
                    'icon': 'fa-whatsapp',
                    'category': 'default',
                    'sequence': 3,
                    'delay_count': 0,
                    'active': True,
                })
            else:
                whatsapp_act.write({
                    'name': 'WhatsApp',
                    'summary': 'WhatsApp',
                    'icon': 'fa-whatsapp',
                    'category': 'default',
                    'sequence': 3,
                    'active': True,
                })

            # 5. 4th: To-Do (sequence 4)
            todo_act = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if todo_act:
                todo_act.sudo().write({'sequence': 4, 'active': True})

            # Check chatter messages for any past done site visits to ensure calendar events exist
            past_messages = self.env['mail.message'].sudo().search([
                ('model', '=', 'crm.lead'),
                ('body', 'ilike', 'Site Visit done'),
            ])
            for msg in past_messages:
                lead = self.env['crm.lead'].sudo().browse(msg.res_id)
                if lead.exists():
                    existing_ev = self.env['calendar.event'].sudo().search([
                        ('opportunity_id', '=', lead.id),
                    ], limit=1)
                    if not existing_ev:
                        self.env['calendar.event'].sudo().create({
                            'name': f"Site Visit: {lead.name}",
                            'opportunity_id': lead.id,
                            'partner_ids': [self.env.user.partner_id.id] + ([lead.partner_id.id] if lead.partner_id else []),
                            'user_id': msg.author_id.user_ids[:1].id or self.env.uid,
                            'start': msg.date or fields.Datetime.now(),
                            'stop': (msg.date or fields.Datetime.now()) + datetime.timedelta(minutes=30),
                            'duration': 0.5,
                            'description': "Site Visit (Completed)",
                        })
        except Exception:
            pass

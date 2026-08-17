# -*- coding: utf-8 -*-
from odoo import models, fields, api
import datetime
import pytz


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    calendar_event_id = fields.Many2one('calendar.event', string="Linked Calendar Event", ondelete='set null')
    call_outcome = fields.Selection([
        ('answered', 'Answered'),
        ('no_answer', 'No answer'),
        ('busy', 'Busy'),
        ('switched_off', 'Switched off'),
    ], string="Call Outcome")

    @api.model_create_multi
    def create(self, vals_list):
        activities = super().create(vals_list)
        for act in activities:
            if act.res_model == 'crm.lead' and act.activity_type_id.name == 'Site Visit' and act.date_deadline:
                lead = self.env['crm.lead'].browse(act.res_id)
                if lead.exists():
                    act._create_or_update_site_visit_event(lead)
        return activities

    def _create_or_update_site_visit_event(self, lead):
        self.ensure_one()
        user_tz_name = self.env.user.tz or 'Asia/Kolkata'
        user_tz = pytz.timezone(user_tz_name)

        start_of_day = user_tz.localize(datetime.datetime.combine(self.date_deadline, datetime.time(0, 0, 0))).astimezone(pytz.utc).replace(tzinfo=None)
        end_of_day = user_tz.localize(datetime.datetime.combine(self.date_deadline, datetime.time(23, 59, 59))).astimezone(pytz.utc).replace(tzinfo=None)

        existing_events_count = self.env['calendar.event'].sudo().search_count([
            ('user_id', '=', self.user_id.id or self.env.uid),
            ('start', '>=', start_of_day),
            ('start', '<=', end_of_day),
        ])

        slot_minutes = existing_events_count * 30
        slot_hour = 10 + (slot_minutes // 60)
        slot_min = slot_minutes % 60

        local_start = user_tz.localize(datetime.datetime.combine(self.date_deadline, datetime.time(slot_hour, slot_min, 0)))
        utc_start = local_start.astimezone(pytz.utc).replace(tzinfo=None)
        utc_stop = utc_start + datetime.timedelta(minutes=30)

        partner_ids = [self.env.user.partner_id.id]
        if lead.partner_id and lead.partner_id.id not in partner_ids:
            partner_ids.append(lead.partner_id.id)

        event = self.env['calendar.event'].sudo().create({
            'name': f"Site Visit: {lead.name}",
            'opportunity_id': lead.id,
            'partner_ids': partner_ids,
            'user_id': self.user_id.id or self.env.uid,
            'start': utc_start,
            'stop': utc_stop,
            'duration': 0.5,
            'description': self.note or f"Site Visit for {lead.name}",
        })
        self.calendar_event_id = event.id

    def _action_done(self, feedback=False, attachment_ids=None):
        for act in self:
            outcome = self.env.context.get('call_outcome') or act.call_outcome
            if outcome:
                outcome_labels = dict(act._fields['call_outcome'].selection)
                label = outcome_labels.get(outcome, outcome)
                outcome_html = f"<div><strong>Call Outcome:</strong> {label}</div>"
                if feedback:
                    feedback = f"{outcome_html}<div>{feedback}</div>"
                else:
                    feedback = outcome_html

                if act.res_model == 'crm.lead':
                    lead = self.env['crm.lead'].browse(act.res_id)
                    if lead.exists():
                        lead.sudo().write({'last_call_outcome': outcome})
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

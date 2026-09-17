# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class MailActivity(models.Model):
    _inherit = "mail.activity"

    call_outcome = fields.Selection([
        ("answered", "Answered"),
        ("no_answer", "No answer"),
        ("busy", "Busy"),
        ("switched_off", "Switched off")
    ], string="Call Outcome")

    def _action_done(self, feedback=False, attachment_ids=None):
        site_visit_leads = self.env['crm.lead']
        for act in self:
            if act.res_model == 'crm.lead' and act.res_id:
                type_name = (act.activity_type_id.name or '').lower()
                summary = (act.summary or '').lower()
                if 'site visit' in type_name or 'site visit' in summary or 'meeting' in type_name:
                    lead = self.env['crm.lead'].browse(act.res_id).exists()
                    if lead:
                        site_visit_leads |= lead

        messages, next_activities = super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

        for lead in site_visit_leads:
            try:
                lead.action_complete_site_visit()
            except Exception as e:
                _logger.error("Error in action_complete_site_visit for lead #%s: %s", lead.id, e)

        return messages, next_activities

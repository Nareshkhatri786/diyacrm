# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CrmLeadWhatsappWizard(models.TransientModel):
    _name = "crm.lead.whatsapp.wizard"
    _description = "Send WhatsApp Follow-up to Lead"

    lead_id = fields.Many2one("crm.lead", string="Lead / Opportunity", required=True, ondelete="cascade")
    lead_name = fields.Char(string="Lead Name", related="lead_id.name", readonly=True)
    phone = fields.Char(string="Phone Number", related="lead_id.phone", readonly=True)
    company_id = fields.Many2one("res.company", related="lead_id.company_id", readonly=True)
    user_id = fields.Many2one("res.users", string="Sales Executive", default=lambda self: self.env.user)
    whatsapp_message_ids = fields.One2many(
        related="lead_id.whatsapp_message_ids",
        readonly=True,
        string="Recent WhatsApp Messages"
    )

    def action_send_connected(self):
        """Send Call Connected follow-up WhatsApp (Project video, location, brochure)."""
        self.ensure_one()
        res = self.lead_id.send_call_followup_whatsapp(
            call_outcome="answered",
            executive_user=self.user_id or self.env.user,
            force_send=True
        )
        if res:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("WhatsApp Sent!"),
                    "message": _("Call Connected WhatsApp message delivered to %s") % self.phone,
                    "type": "success",
                    "sticky": False
                }
            }
        else:
            raise UserError(_("Could not send WhatsApp message. Please verify phone number and Meta credentials."))

    def action_send_missed(self):
        """Send Missed/Busy Call follow-up WhatsApp (Call back request, executive details)."""
        self.ensure_one()
        res = self.lead_id.send_call_followup_whatsapp(
            call_outcome="no_answer",
            executive_user=self.user_id or self.env.user,
            force_send=True
        )
        if res:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("WhatsApp Sent!"),
                    "message": _("Missed Call WhatsApp message delivered to %s") % self.phone,
                    "type": "success",
                    "sticky": False
                }
            }
        else:
            raise UserError(_("Could not send WhatsApp message. Please verify phone number and Meta credentials."))

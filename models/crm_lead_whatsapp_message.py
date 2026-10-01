# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CrmLeadWhatsappMessage(models.Model):
    _name = "crm.lead.whatsapp.message"
    _description = "CRM Lead WhatsApp Message History"
    _order = "date desc, id desc"

    lead_id = fields.Many2one("crm.lead", string="Lead / Opportunity", ondelete="cascade", required=True, index=True)
    direction = fields.Selection([
        ("inbound", "Incoming (Client)"),
        ("outbound", "Outgoing (Staff / System)")
    ], string="Direction", default="inbound", required=True, index=True)

    author_name = fields.Char("Sender / Staff Name", default="Client")
    phone = fields.Char("Phone Number")
    body = fields.Text("Message Content", required=True)
    date = fields.Datetime("Date & Time", default=fields.Datetime.now, index=True)
    company_id = fields.Many2one(related="lead_id.company_id", store=True, readonly=True, index=True)

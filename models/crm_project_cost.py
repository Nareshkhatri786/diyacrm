# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CrmProjectCost(models.Model):
    _name = "crm.project.cost"
    _description = "Per-Project Lead Acquisition Cost"
    _order = "company_id asc"

    company_id = fields.Many2one(
        "res.company",
        string="Project / Company",
        required=True,
        ondelete="cascade",
        index=True,
    )
    cost_per_lead = fields.Float(
        string="Cost Per Lead (₹)",
        default=70.0,
        digits=(10, 2),
        help="Estimated acquisition cost per lead for this project in Indian Rupees.",
    )
    notes = fields.Char(string="Notes / Remarks")

    @api.constrains('company_id')
    def _check_unique_company(self):
        for rec in self:
            domain = [
                ('company_id', '=', rec.company_id.id),
                ('id', '!=', rec.id),
            ]
            if self.search_count(domain):
                raise ValidationError(_("A cost entry already exists for this project/company."))

    @api.model
    def get_cost_map(self):
        """Returns dict: {company_id: cost_per_lead}"""
        records = self.search([])
        return {r.company_id.id: r.cost_per_lead for r in records}

    @api.model
    def get_cost_for_company(self, company_id, default=70.0):
        rec = self.search([("company_id", "=", company_id)], limit=1)
        return rec.cost_per_lead if rec else default

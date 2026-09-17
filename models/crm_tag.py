# -*- coding: utf-8 -*-
from odoo import models, fields


class CrmTag(models.Model):
    _inherit = 'crm.tag'

    company_ids = fields.Many2many(
        'res.company',
        'crm_tag_company_rel',
        'tag_id', 'company_id',
        string='Companies',
        help='Agar blank ho to sabhi companies me dikhe'
    )

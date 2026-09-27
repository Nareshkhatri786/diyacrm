# -*- coding: utf-8 -*-
from odoo import models

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """
        Ensure home_action_id points to CRM Pipeline for all non-admin users,
        so upon opening /odoo or logging in, the web client directly launches CRM.
        """
        res = super().session_info()
        user = self.env.user
        if not user.has_group('base.group_system'):
            crm_action = self.env.ref('crm.action_your_pipeline', raise_if_not_found=False) or \
                         self.env.ref('crm.crm_lead_action_pipeline', raise_if_not_found=False)
            if crm_action:
                res['home_action_id'] = crm_action.id
        return res

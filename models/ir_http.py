# -*- coding: utf-8 -*-
from odoo import models

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """
        Ensure home_action_id points to Visual Unit Matrix for Developer users,
        and CRM Pipeline for regular sales staff.
        Whitelabel support URL.
        """
        res = super().session_info()
        res['support_url'] = "https://sigprop.in"

        user = self.env.user
        if not user.has_group('base.group_system'):
            is_developer_only = (
                user.has_group('diyacrm.group_property_developer')
                and not user.has_group('sales_team.group_sale_salesman')
            )
            if is_developer_only:
                matrix_action = self.env.ref('diyacrm.action_crm_unit_matrix', raise_if_not_found=False) or \
                                self.env.ref('diyacrm.action_crm_property_unit_list', raise_if_not_found=False)
                if matrix_action:
                    res['home_action_id'] = matrix_action.id
            else:
                crm_action = self.env.ref('crm.action_your_pipeline', raise_if_not_found=False) or \
                             self.env.ref('crm.crm_lead_action_pipeline', raise_if_not_found=False)
                if crm_action:
                    res['home_action_id'] = crm_action.id
        return res

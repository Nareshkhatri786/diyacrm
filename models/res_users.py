# -*- coding: utf-8 -*-
from odoo import models, api

class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        crm_action = self.env.ref('crm.action_your_pipeline', raise_if_not_found=False) or \
                     self.env.ref('crm.crm_lead_action_pipeline', raise_if_not_found=False)
        admin_group = self.env.ref('base.group_system', raise_if_not_found=False)

        for vals in vals_list:
            if crm_action and not vals.get('action_id'):
                groups_id = vals.get('groups_id', [])
                is_admin = False
                if admin_group:
                    for g in groups_id:
                        if isinstance(g, (list, tuple)) and len(g) >= 2:
                            if g[0] == 4 and g[1] == admin_group.id:
                                is_admin = True
                                break
                            elif g[0] == 6 and len(g) >= 3 and admin_group.id in g[2]:
                                is_admin = True
                                break
                if not is_admin:
                    vals['action_id'] = crm_action.id

        return super().create(vals_list)

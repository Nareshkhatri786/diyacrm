# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = "res.users"

    is_property_developer = fields.Boolean(
        string="Developer (Unit Inventory Only)",
        compute="_compute_is_property_developer",
        inverse="_inverse_is_property_developer",
        help="Check this to restrict the user to Unit Inventory and Visual Matrix only. Blocks access to CRM leads, pipeline, attendance, etc."
    )

    def _compute_is_property_developer(self):
        for user in self:
            user.is_property_developer = user.has_group('diyacrm.group_property_developer')

    def _inverse_is_property_developer(self):
        dev_group = self.env.ref('diyacrm.group_property_developer', raise_if_not_found=False)
        sales_group = self.env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
        sales_mgr_group = self.env.ref('sales_team.group_sale_manager', raise_if_not_found=False)
        att_group = self.env.ref('hr_attendance.group_hr_attendance_user', raise_if_not_found=False)
        att_mgr_group = self.env.ref('hr_attendance.group_hr_attendance_manager', raise_if_not_found=False)
        matrix_action = self.env.ref('diyacrm.action_crm_unit_matrix', raise_if_not_found=False) or \
                        self.env.ref('diyacrm.action_crm_property_unit_list', raise_if_not_found=False)

        if not dev_group:
            return

        for user in self:
            if user.is_property_developer:
                cmds = [(4, dev_group.id)]
                for g in [sales_group, sales_mgr_group, att_group, att_mgr_group]:
                    if g:
                        cmds.append((3, g.id))
                user.write({'group_ids': cmds})
                if matrix_action:
                    user.sudo().write({'action_id': matrix_action.id})
            else:
                user.write({'group_ids': [(3, dev_group.id)]})

    @api.model_create_multi
    def create(self, vals_list):
        crm_action = self.env.ref('crm.action_your_pipeline', raise_if_not_found=False) or \
                     self.env.ref('crm.crm_lead_action_pipeline', raise_if_not_found=False)
        matrix_action = self.env.ref('diyacrm.action_crm_unit_matrix', raise_if_not_found=False) or \
                        self.env.ref('diyacrm.action_crm_property_unit_list', raise_if_not_found=False)
        admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
        dev_group = self.env.ref('diyacrm.group_property_developer', raise_if_not_found=False)

        for vals in vals_list:
            if not vals.get('action_id'):
                raw_groups = vals.get('group_ids', vals.get('groups_id', []))
                is_admin = False
                is_dev = False
                if admin_group or dev_group:
                    for g in raw_groups:
                        if isinstance(g, (list, tuple)) and len(g) >= 2:
                            g_ids = [g[1]] if g[0] == 4 else (g[2] if g[0] == 6 and len(g) >= 3 else [])
                            if admin_group and admin_group.id in g_ids:
                                is_admin = True
                            if dev_group and dev_group.id in g_ids:
                                is_dev = True

                if not is_admin:
                    if is_dev and matrix_action:
                        vals['action_id'] = matrix_action.id
                    elif crm_action:
                        vals['action_id'] = crm_action.id

        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        dev_group = self.env.ref('diyacrm.group_property_developer', raise_if_not_found=False)
        matrix_action = self.env.ref('diyacrm.action_crm_unit_matrix', raise_if_not_found=False) or \
                        self.env.ref('diyacrm.action_crm_property_unit_list', raise_if_not_found=False)
        if dev_group and matrix_action:
            for user in self:
                if user.has_group('diyacrm.group_property_developer') and not user.has_group('sales_team.group_sale_salesman') and not user.has_group('base.group_system'):
                    if user.action_id != matrix_action:
                        user.sudo().action_id = matrix_action.id
        return res

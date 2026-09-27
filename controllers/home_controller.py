# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home

class HomeCustom(Home):

    def _login_redirect(self, uid, redirect=None):
        """
        Directly redirect non-admin users to CRM Pipeline upon login
        instead of generic /odoo home or other modules.
        """
        if not redirect:
            user = request.env['res.users'].sudo().browse(uid)
            if not user.has_group('base.group_system'):
                crm_action = request.env.ref('crm.action_your_pipeline', raise_if_not_found=False) or \
                             request.env.ref('crm.crm_lead_action_pipeline', raise_if_not_found=False)
                if crm_action:
                    return f'/odoo/action-{crm_action.id}'
        return super()._login_redirect(uid, redirect=redirect)

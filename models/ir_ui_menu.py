# -*- coding: utf-8 -*-
from odoo import models

class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def load_web_menus(self, debug):
        """
        Non-admin users should only see CRM and Attendances in the app drawer/switcher.
        Admin continues to have full visibility of all applications and settings.
        """
        web_menus = super().load_web_menus(debug)
        user = self.env.user

        # Administrators keep full access to all apps
        if not user.has_group('base.group_system'):
            allowed_xmlids = [
                'crm.crm_menu_root',
                'hr_attendance.menu_hr_attendance_root',
            ]
            allowed_ids = set()
            for xmlid in allowed_xmlids:
                menu = self.env.ref(xmlid, raise_if_not_found=False)
                if menu:
                    allowed_ids.add(menu.id)

            if 'root' in web_menus and allowed_ids:
                root_children = web_menus['root'].get('children', [])
                filtered_children = [cid for cid in root_children if cid in allowed_ids]
                # Ensure CRM is first if present
                crm_menu = self.env.ref('crm.crm_menu_root', raise_if_not_found=False)
                if crm_menu and crm_menu.id in filtered_children:
                    filtered_children.remove(crm_menu.id)
                    filtered_children.insert(0, crm_menu.id)
                web_menus['root']['children'] = filtered_children

        return web_menus

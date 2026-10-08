# -*- coding: utf-8 -*-
from odoo import models

class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def load_web_menus(self, debug):
        """
        App drawer / Switcher visibility rules:
        - Administrators: Full access to all applications and settings.
        - Developers (group_property_developer without CRM/sales groups):
          See ONLY 'Unit Inventory' in the entire app switcher.
        - Internal Sales Staff:
          See CRM, Unit Inventory, and Attendances.
        """
        web_menus = super().load_web_menus(debug)
        user = self.env.user

        # Administrators keep full access to all apps
        if not user.has_group('base.group_system'):
            is_developer_only = (
                user.has_group('diyacrm.group_property_developer')
                and not user.has_group('sales_team.group_sale_salesman')
            )

            if is_developer_only:
                allowed_xmlids = [
                    'diyacrm.menu_crm_property_unit_top',
                ]
            else:
                allowed_xmlids = [
                    'crm.crm_menu_root',
                    'hr_attendance.menu_hr_attendance_root',
                    'diyacrm.menu_crm_property_unit_top',
                ]

            allowed_ids = set()
            for xmlid in allowed_xmlids:
                menu = self.env.ref(xmlid, raise_if_not_found=False)
                if menu:
                    allowed_ids.add(menu.id)

            if 'root' in web_menus and allowed_ids:
                root_children = web_menus['root'].get('children', [])
                filtered_children = [cid for cid in root_children if cid in allowed_ids]

                # For sales staff, keep CRM first
                if not is_developer_only:
                    crm_menu = self.env.ref('crm.crm_menu_root', raise_if_not_found=False)
                    if crm_menu and crm_menu.id in filtered_children:
                        filtered_children.remove(crm_menu.id)
                        filtered_children.insert(0, crm_menu.id)

                web_menus['root']['children'] = filtered_children

        return web_menus

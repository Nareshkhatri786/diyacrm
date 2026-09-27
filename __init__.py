# -*- coding: utf-8 -*-
from . import models
from . import controllers
from . import wizard


def post_init_hook(env):
    """Module install/upgrade ke baad company-wise tags assign karo aur non-admins ko CRM home action do."""
    _assign_tag_companies(env)
    _set_non_admin_home_action(env)


def _set_non_admin_home_action(env):
    """Set default home action to CRM Pipeline for all non-admin internal users."""
    crm_action = env.ref('crm.action_your_pipeline', raise_if_not_found=False) or \
                 env.ref('crm.crm_lead_action_pipeline', raise_if_not_found=False)
    if not crm_action:
        return
    admin_group = env.ref('base.group_system', raise_if_not_found=False)
    if not admin_group:
        return
    non_admins = env['res.users'].search([
        ('groups_id', 'not in', admin_group.id),
        ('share', '=', False),
    ])
    if non_admins:
        non_admins.write({'action_id': crm_action.id})
        print(f"[diyacrm] Set CRM home action for {len(non_admins)} non-admin users.")


def _assign_tag_companies(env):
    def get_co(name_part):
        return env['res.company'].search([('name', 'ilike', name_part)], limit=1)

    shreemad = get_co('shreemad')
    royal    = get_co('royal')
    the1st   = get_co('1st')
    devi     = get_co('devi')

    print(f"[diyacrm] Companies: shreemad={shreemad.name or 'N/A'}, "
          f"royal={royal.name or 'N/A'}, the1st={the1st.name or 'N/A'}, "
          f"devi={devi.name or 'N/A'}")

    tags_map = {
        'A-Block':      [shreemad, royal, the1st],
        'B-Block':      [shreemad, royal, the1st],
        'C-Block':      [shreemad, royal, the1st],
        'D-Block':      [shreemad, royal],
        '265 sq yards': [the1st],
        '270 sq yards': [the1st],
        '275 sq yards': [the1st],
        '285 sq yards': [shreemad],
        '290 sq yards': [shreemad],
        '315 sq yards': [shreemad],
        '380 sq yards': [shreemad],
        '400 sq yards': [shreemad],
        '230 sq yards': [royal],
        '240 sq yards': [royal],
        '242 sq yards': [royal],
        '298 sq yards': [royal],
        '318 sq yards': [royal],
        '434 sq yards': [royal],
        '85 sq yards':  [devi],
        '90 sq yards':  [devi],
        '110 sq yards': [devi],
    }

    CrmTag = env['crm.tag']
    for tag_name, companies in tags_map.items():
        valid = [c for c in companies if c]
        if not valid:
            continue
        tag = CrmTag.search([('name', '=', tag_name)], limit=1)
        if tag:
            tag.company_ids = [(6, 0, [c.id for c in valid])]
            print(f"[diyacrm] Tag '{tag_name}' → {[c.name for c in valid]}")

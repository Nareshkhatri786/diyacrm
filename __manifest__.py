{
    'name': 'Diya CRM',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Custom CRM Enhancements, Telecalling Dashboard and Tweaks for Diya CRM',
    'description': """
        Diya CRM Custom Addon
        =====================
        This module manages all customizations, new fields, live executive dashboard, 
        and UI tweaks for CRM without touching core Odoo files.
    """,
    'author': 'Diya CRM',
    'website': 'https://www.diyacrm.com',
    'license': 'LGPL-3',
    'depends': ['base', 'crm', 'mail', 'utm', 'calendar'],
    'data': [
        'data/utm_source_data.xml',
        'data/mail_activity_type_data.xml',
        'views/crm_lead_views.xml',
        'views/mail_activity_views.xml',
        'views/crm_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'diyacrm/static/src/css/crm_custom.css',
            'diyacrm/static/src/core/web/activity_markasdone_patch.xml',
            'diyacrm/static/src/core/web/activity_markasdone_patch.js',
            'diyacrm/static/src/dashboard/crm_dashboard.xml',
            'diyacrm/static/src/dashboard/crm_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}

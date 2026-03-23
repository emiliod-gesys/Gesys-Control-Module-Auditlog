# -*- coding: utf-8 -*-
{
    'name': 'Control - User Activity Audit (v19)',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Audit user activity, key business actions and usage statistics',
    'description': """
User Control & Activity Tracking
================================
This module records and monitors all user actions across the system for audit and compliance.

Features:
---------
* Logs key user actions: validations, invoices, payments, cancellations and tracked operations
* Recent actions view and history grouped by employee and date
* Configurable rules per model (exclude users or fields from logging)
* Activity dashboard and statistics with charts
* PDF/Excel statistics reports by day, week or month
* Optional automatic purge of old records (cron)
* Timezone and language (English/Spanish) support
* Two security groups: User (view) and Manager (config + rules)
    """,
    'author': 'Gesys',
    'maintainer': 'Gesys',
    'website': 'https://gesysgt.odoo.com',
    'support': 'emiliodiaz@gesys.gt',
    'images': [
        'static/description/images/main_screenshot.png',
        'static/description/images/main_screenshot.gif',
        'static/description/images/user_actions_1.png',
        'static/description/images/user_actions_2.png',
        'static/description/images/actions_by_employee_1.png',
        'static/description/images/change_lines_1.png',
        'static/description/images/user_activity_1.png',
        'static/description/images/statistics_1.png',
        'static/description/images/rules_1.png',
        'static/description/images/configuration_1.png',
    ],
    'depends': ['base', 'mail', 'account', 'web', 'sale', 'purchase'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/cron_data.xml',
        'views/user_action_views.xml',
        'views/user_action_line_views.xml',
        'views/user_action_rule_views.xml',
        'views/user_action_bindings.xml',
        'views/user_action_config_views.xml',
        'views/res_users_views.xml',
        'views/user_action_purge_wizard_views.xml',
        'views/user_activity_dashboard.xml',
        'report/statistics_reports.xml',
        'views/menu_views.xml',
        'report/user_manual_reports.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gesys_control_users_v19/static/src/js/user_activity_dashboard.js',
            'gesys_control_users_v19/static/src/xml/user_activity_dashboard.xml',
            'gesys_control_users_v19/static/src/scss/user_activity_dashboard.scss',
            'gesys_control_users_v19/static/src/js/statistics_dashboard.js',
            'gesys_control_users_v19/static/src/xml/statistics_dashboard.xml',
            'gesys_control_users_v19/static/src/scss/statistics_dashboard.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 12,
    'currency': 'USD',
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
}
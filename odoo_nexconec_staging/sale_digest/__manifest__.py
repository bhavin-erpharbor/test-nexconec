# -*- coding: utf-8 -*-
{
    'name': 'Digest Commercial Hebdomadaire',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': "Digest hebdomadaire + rapport mensuel + rapport activités ciblé",
    'author': 'Votre Société',
    'depends': ['sale_crm', 'account', 'mail', 'calendar'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_digest.xml',
        'data/mail_template_monthly_report.xml',
        'data/mail_template_activity_report.xml',
        'data/ir_cron_digest.xml',
        'views/sale_digest_views.xml',
        'views/res_users_views.xml',
        'views/activity_report_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

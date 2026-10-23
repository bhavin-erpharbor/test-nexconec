# -*- encoding: utf-8 -*-
{
    'name': 'SCS Website Extend',
    'category': 'website',
    'sequence': 1,
    'summary': 'SCS Website Extend',
    'website': 'http://www.serpentcs.com',
    'version': '19.0.1.0.1',
    'description': "SCS Website Extend",
    'depends': ['sale', 'website_sale'],
    'data': [
        "views/portal_templates.xml",
        "views/website_templates.xml",
    ],
    'installable': True,
    'application': True,
}

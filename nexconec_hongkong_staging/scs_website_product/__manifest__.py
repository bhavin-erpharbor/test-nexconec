# -*- encoding: utf-8 -*-
{
    'name': 'SCS Website Product',
    'category': 'website',
    'sequence': 1,
    'summary': 'SCS Website Product',
    'website': 'http://www.serpentcs.com',
    'version': '19.0.1.0.1',
    'description': "SCS Website Product",
    'depends': ['sale', 'website_sale', 'scs_customization'],
    'data': [
        "views/product_public_category_view.xml",
        "views/website_templates.xml",
        "views/res_partner_view.xml",
        "views/sale_order_views.xml",
    ],
    'assets': {
        'web.assets_frontend': [
            'scs_website_product/static/src/js/**/*',
            'scs_website_product/static/src/xml/website_sale_stock.xml',
        ],
    },
    'installable': True,
    'application': True,
}

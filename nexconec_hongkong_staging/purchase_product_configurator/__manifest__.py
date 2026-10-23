# -*- encoding: utf-8 -*-
{
    'name': 'Purchase Product Configurator',
    'category': 'purchase',
    'sequence': 1,
    'summary': 'Purchase Product Configurator',
    'website': 'http://www.serpentcs.com',
    'version': '19.0.1.0.1',
    'description': "Purchase Product Configurator",
    'depends': ['web','sale','sale_product_matrix', 'purchase_product_matrix'],
    'data': [
       'security/ir.model.access.csv',
       'views/purchase_views.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "purchase_product_configurator/static/src/js/purchase_product_field.js",
            "purchase_product_configurator/static/src/js/product_configurator_hook.js",
            "purchase_product_configurator/static/src/xml/purchase_product_configurator.xml"
        ],
    },
    'installable': True,
    'application': True,
}

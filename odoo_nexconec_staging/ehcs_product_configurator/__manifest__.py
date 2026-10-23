{
    "name" : "EHCS Product Configurator",
    "author" : "ERP Harbor",
    "version" : "19.0.1.0.0",
    "license" : "LGPL-3",
    "category" : "EHCS Base",
    "description" : "Create multiple variant from same product configurator",
    'website':'www.erpharbor.com',
    'depends': [
        'sale_management',
        'website_sale',
    ],
    "data" : [
        'views/product_attribute_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/ehcs_product_configurator/static/src/js/product_configurator_dialog.js',
            '/ehcs_product_configurator/static/src/js/sale_product_fields.js',
            # '/ehcs_product_configurator/static/src/js/purchase_product_fields.js',
            '/ehcs_product_configurator/static/src/xml/product_configurator.xml',
            '/ehcs_product_configurator/static/src/css/configurator.scss',
        ],
        'web.assets_frontend': [
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}

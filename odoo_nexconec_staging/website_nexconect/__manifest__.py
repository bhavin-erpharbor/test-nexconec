# -*- encoding: utf-8 -*-
{
    'name': 'Website Nexconect',
    'category': 'Website/Website',
    'sequence': 1,
    'summary': 'Website nexconect',
    'website': 'http://www.serpentcs.com',
    'version': '19.0.1.0.8',
    'description': "Website related changes made for nexconect",
    'depends': ['sale', 'website_sale','purchase_product_configurator',
               'website_sale_stock','website_studio','stock_delivery',
               'scs_bom_xls_report'],
    'data': [
        'data/mail_template.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/v17_ir_ui_view_mig.xml',
        'views/header.xml',
        # 'views/assests.xml',
        'views/report_templates.xml',
        'views/stock_picking.xml',
        'views/account_move.xml',
        'views/sale_order_views.xml',
        'reports/sale_report.xml',
        'reports/report_delivery_document.xml',
        'reports/purchaseorder_document.xml',
        'reports/purchasequotation_document.xml',
        'reports/report_invoice_document.xml',
        'reports/mrp_production_templates.xml',
        'views/website_sale.xml',
        'views/product.xml',
        'views/res_partner_view.xml',
        'views/purchase_order_views.xml',
        'views/product_template_view.xml',
        'views/sale_portal_templates.xml',
        'data/data.xml'
    ],
    'assets': {
        'web.assets_backend': [
            '/website_nexconect/static/src/js/list_renderer.js',
            ],
        'web.assets_frontend': [
            '/website_nexconect/static/src/xml/website_sale_stock.xml',
            # '/website_nexconect/static/src/js/sale_variant_mixin.js',
            '/website_nexconect/static/src/js/variant_mixin.js',
            '/website_nexconect/static/src/js/website_cutting_popup.js',
            '/website_nexconect/static/src/js/cart_cutting_recap.js',
            '/website_nexconect/static/src/scss/style.scss',
            # '/website_nexconect/static/src/js/website_disable_qty_cart.js',
            (
                'before',
                'website_sale/static/src/interactions/website_sale.js',
                '/website_nexconect/static/src/js/sale_variant_mixin.js',
            ),


        ]
    },
    'demo': [],
    "license": "LGPL-3",
    'installable': True,
    'external_dependencies': {},
    'application': True,
}

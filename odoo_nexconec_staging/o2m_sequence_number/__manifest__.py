# -*- coding: utf-8 -*-
{
    "name": "Set sequence number to One2many",
    "summary": "Set Sequence number to One2many",
    "version": "19.0.1.0.3",
    "author": "Serpentcs",
    "website": "www.serpentcs.com",
    "description": """Add sequence number in sale order line, invoice line,
        and purchase line""",
    "category": "sale",
    "license": "LGPL-3",
    "depends": ["sale_purchase", "stock", "purchase_product_matrix", "website_sale"],
    "images": ["static/description/logo.png"],
    "data": [
        "view/purchase_view.xml",
        "view/sale_view.xml",
        "view/stock_view.xml",
        "view/account_move.xml",
    ],
    "assets": {
        "web.assets_backend": [
          "o2m_sequence_number/static/src/scss/form_controller.scss",
        ],
    },
    "installable": True,
}

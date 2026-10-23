# -*- coding: utf-8 -*-

{
    "name": "Sale Lot Availability",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Affichage des lots disponibles",
    "author": "Nexconec",
    "depends": [
        "sale_management",
        "stock",
    ],
    "data": [
        "views/sale_order_line_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "sale_lot_availability/static/src/js/lot_availability_widget.js",
            "sale_lot_availability/static/src/xml/lot_availability_widget.xml",
        ],
    },
    "installable": True,
    "application": False,
    "license": "AGPL-3",
}

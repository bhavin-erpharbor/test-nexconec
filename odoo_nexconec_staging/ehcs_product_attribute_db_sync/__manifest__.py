{
    "name": "EHCS France Product DB Sync",
    "version": "19.0.1.1.0",
    "summary": "Push products, variants, attributes and values from France DB to Hong Kong DB using XML-RPC",
    "category": "Inventory/Product",
    "author": "EHCS",
    "depends": ["base", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "data/ir_cron.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}

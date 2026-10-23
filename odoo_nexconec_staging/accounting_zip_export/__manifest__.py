{
    "name": "Accounting ZIP Export",
    "summary": "Export accounting documents for previous month as ZIP",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/accounting_zip_export_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}

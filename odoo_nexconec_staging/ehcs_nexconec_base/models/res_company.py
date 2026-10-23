from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    export_po_list_vendor_id = fields.Many2one('res.partner', string="Export PO List To Vendor")

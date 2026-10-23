# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    export_po_list_vendor_id = fields.Many2one(related="company_id.export_po_list_vendor_id", readonly=False)

# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    product_quantity = fields.Integer(default=1)

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()
        data['product_quantity'] = self.product_quantity
        return xml_id, data

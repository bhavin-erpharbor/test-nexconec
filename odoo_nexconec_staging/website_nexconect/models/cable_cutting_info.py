# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CableCuttingInfo(models.Model):
    _name = 'cable.cutting.info'
    _description = 'Cable Cutting Info'

    sale_order_id = fields.Many2one('sale.order', 'Sale Order')
    picking_id = fields.Many2one('stock.picking', 'Stock Picking')
    no_of_piece = fields.Integer('No. of Piece')
    no_of_meter = fields.Float('No. of Meter')
    product_id = fields.Many2one('product.product', string='Product')

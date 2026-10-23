# -*- coding: utf-8 -*-
from odoo import models, api, fields

class StockMove(models.Model):
    _inherit = 'stock.move'

    sequence_no = fields.Integer('No.', compute="_sequence_no")

    @api.depends('picking_id.move_ids', 'picking_id.move_ids.product_id')
    def _sequence_no(self):
        for move in self:
            count = 0
            for mv in move.picking_id.move_ids:
                count += 1
                mv.sequence_no = count

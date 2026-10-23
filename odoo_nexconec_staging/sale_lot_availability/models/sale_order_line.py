# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    available_lots_count = fields.Integer(
        string="Lots disponibles",
        compute="_compute_lot_availability",
    )

    lot_tooltip = fields.Char(
        compute="_compute_lot_availability",
    )

    @api.depends("product_id", "product_uom_qty")
    def _compute_lot_availability(self):
        StockQuant = self.env["stock.quant"]

        for line in self:
            line.available_lots_count = 0
            line.lot_tooltip = ""

            if not line.product_id:
                continue

            quants = StockQuant.search([
                ("product_id", "=", line.product_id.id),
                ("lot_id", "!=", False),
                ("quantity", ">", 0),
                ("location_id.usage", "=", "internal"),
            ])

            details = []
            for quant in quants:
                details.append(f"{quant.lot_id.name} : {int(quant.quantity)}")

            line.available_lots_count = len(quants)
            line.lot_tooltip = "\n".join(details)

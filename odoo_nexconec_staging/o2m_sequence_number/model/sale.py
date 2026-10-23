# -*- coding: utf-8 -*-
from odoo import models, api, fields


# class StockRule(models.Model):
#     _inherit = 'stock.rule'
#  
#     sequence_no = fields.Integer('No.', help="Gives the sequence order when displaying a list of sales order lines.")
#  
#     def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
#         result = super(StockRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, values, group_id)
#         if values.get('sequence_no', False):
#             result['sequence_no'] = values['sequence_no']
#         return result


class SaleOrder(models.Model):
    _inherit = "sale.order"

    x_studio_partner_company = fields.Many2one('res.partner',
        compute='compute_partner_company', string='Partner Company')

    def compute_partner_company(self):
        for sale in self:
            if sale.partner_id and sale.partner_id.parent_id:
                sale.x_studio_partner_company = sale.partner_id.parent_id.id
            else:
                sale.x_studio_partner_company = sale.partner_id.id


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sequence_no = fields.Integer(
        string="No.",
        compute="_compute_sequence_no",
        store=False,
    )

    @api.depends(
        "order_id",
        "order_id.order_line",
        "order_id.order_line.sequence",
        "order_id.order_line.display_type",
    )
    def _compute_sequence_no(self):
        """
        Compute serial number for sale order lines.

        Section and note lines are skipped and get 0.
        Normal lines get 1, 2, 3... per sale order.
        """

        # Default value for all current records
        for line in self:
            line.sequence_no = 0

        # Compute numbering per order
        for order in self.mapped("order_id"):
            number = 0

            for line in order.order_line.sorted(
                key=lambda l: (l.sequence, l.id)
            ):
                if line.display_type in ("line_section", "line_note"):
                    line.sequence_no = 0
                    continue

                number += 1
                line.sequence_no = number

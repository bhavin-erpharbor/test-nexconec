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
    _inherit = 'sale.order.line'

    sequence_no = fields.Integer('No.', compute="_sequence_no")

    def _prepare_procurement_values(self):
        self.ensure_one()
        vals = super(SaleOrderLine, self)._prepare_procurement_values()
        vals.update({'sequence_ref':self.sequence_no})
        return vals

    def _prepare_invoice_line(self, **optional_values):
        vals = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        vals.update({'sequence_no':self.sequence_no})
        return vals

    @api.depends('sequence', 'order_id')
    def _sequence_no(self):
        for order_line in self:
            if order_line.display_type not in ['line_section', 'line_note']:
                # for not changing sequence of existing line after write
                if not order_line.sequence_no:
                    serial_no = 1
                    for line in order_line.mapped('order_id').order_line:
                        if line.display_type not in ['line_section', 'line_note']:
                            line.sequence_no = serial_no
                            serial_no += 1
                        else:
                            line.sequence_no = 0
            else:
                order_line.sequence_no = 0

# See LICENSE file for full copyright and licensing details. 
from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = "account.move"

    delivery_message = fields.Text('Delivery Message')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sale_line_id'):
                order = self.env['sale.order.line'].sudo().browse(int(vals.get('sale_line_id'))).order_id
                if order and order.x_studio_delivery_message:
                    vals.update({'delivery_message': order.x_studio_delivery_message})
        return super(AccountMove, self).create(vals_list)

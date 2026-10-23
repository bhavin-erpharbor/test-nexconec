from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_shipping_id = fields.Many2one(tracking=1)

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            order.message_subscribe([order.partner_id.id])
        return res

    def _compute_partner_shipping_id(self):
        super(SaleOrder, self)._compute_partner_shipping_id()
        for order in self.filtered(lambda s: not s.website_id):
            if order.partner_id and order.partner_id.child_ids:
                if len(order.partner_id.child_ids.filtered(lambda l: l.type == 'delivery')) > 1:
                    default_delivery_address = order.partner_id.child_ids.filtered(
                        lambda c: c.is_default_delivery_address)
                    if default_delivery_address:
                        order.partner_shipping_id = default_delivery_address[0]
                    elif order.partner_id:
                        order.partner_shipping_id = order.partner_id.id

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if vals.get('partner_shipping_id'):
            for order in self:
                if order.picking_ids:
                    out_transfers = order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
                    if out_transfers:
                        out_transfers.write({'partner_id': order.partner_shipping_id.id})
        return res

    @api.onchange('partner_shipping_id')
    def _onchange_partner_shipping_id(self):
        res = super(SaleOrder, self)._onchange_partner_shipping_id()
        if 'Do not forget to change the partner' in res.get('warning', {}).get('message', ''):
            pickings = self.picking_ids.filtered(
                lambda p: p.state not in ['done', 'cancel'] and p.partner_id != self.partner_shipping_id
            )
            if pickings:
                res['warning'] = {
                    'title': _('Automatic Action'),
                    'message': _(
                        'Partner will be automatically gets updated on the following delivery orders: %s',
                        ','.join(pickings.mapped('name')))
                }
        return res

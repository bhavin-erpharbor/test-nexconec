from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = "stock.move"

    def _prepare_procurement_values(self):
        res = super(StockMove, self)._prepare_procurement_values()
        if self.sale_line_id:
            res.update({'so_line_id': self.sale_line_id,
                'code_intern': self.sale_line_id._get_code_intern_description()})
        return res

    def _get_new_picking_values(self):
        vals = super()._get_new_picking_values()
        sale_orders = self.mapped('sale_line_id.order_id')
        cable_lines = []

        for sale in sale_orders:
            for cable in sale.cutting_info_ids:
                cable_lines.append((0, 0, {
                    'product_id': cable.product_id.id,
                    'no_of_piece': cable.no_of_piece,
                    'no_of_meter': cable.no_of_meter,
                }))

        vals.update({
            'cutting_info_ids': cable_lines
        })

        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sale_line_id'):
                line = self.env['sale.order.line'].sudo().browse(
                    int(vals.get('sale_line_id')))
                vals.update({
                    'description_picking': line.name
                })
        return super(StockMove, self).create(vals_list)


class StockPicking(models.Model):
    _inherit="stock.picking"

    delivery_message=fields.Text('Delivery Message')
    cutting_info_ids = fields.One2many('cable.cutting.info', 'picking_id', string="Cutting Infos")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('origin'):
                order=self.env['sale.order'].search(
                [('name', '=', vals.get('origin'))], limit=1)
                if order and order.x_studio_delivery_message:
                    vals.update({'delivery_message': order.x_studio_delivery_message})
        return super(StockPicking, self).create(vals_list)

    @ api.depends('move_ids.date_deadline', 'move_type')
    def _compute_date_deadline(self):
        for picking in self:
            picking.date_deadline=max(picking.move_ids.filtered(
                'date_deadline').mapped('date_deadline'), default=False)

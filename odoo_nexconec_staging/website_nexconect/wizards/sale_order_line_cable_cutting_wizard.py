from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrderLineCableCuttingWizard(models.TransientModel):
    _name = 'sale.order.line.cable.cutting.wizard'
    _description = 'Sale Order Line Cable Cutting Wizard'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True
    )

    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string='Sale Order Line',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )

    line_ids = fields.One2many(
        'sale.order.line.cable.cutting.wizard.line',
        'wizard_id',
        string='Cutting Lines'
    )

    total_length = fields.Float(
        string='Total Length',
        compute='_compute_totals'
    )

    total_pieces = fields.Integer(
        string='Total Pieces',
        compute='_compute_totals'
    )

    @api.depends('line_ids.no_of_piece', 'line_ids.no_of_meter')
    def _compute_totals(self):
        for wizard in self:
            total_length = 0.0
            total_pieces = 0

            for line in wizard.line_ids:
                total_length += line.no_of_piece * line.no_of_meter
                total_pieces += line.no_of_piece

            wizard.total_length = total_length
            wizard.total_pieces = total_pieces

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        sale_order_line_id = self.env.context.get('active_id')
        if sale_order_line_id:
            sale_order_line = self.env['sale.order.line'].browse(sale_order_line_id)

            res.update({
                'sale_order_id': sale_order_line.order_id.id,
                'sale_order_line_id': sale_order_line.id,
                'product_id': sale_order_line.product_id.id,
            })

            # Load existing cutting info for edit
            existing_lines = sale_order_line.cutting_info_ids
            if existing_lines:
                res['line_ids'] = [
                    (0, 0, {
                        'no_of_piece': cut.no_of_piece,
                        'no_of_meter': cut.no_of_meter,
                    })
                    for cut in existing_lines
                ]

        return res

    def action_confirm(self):
        self.ensure_one()

        if not self.line_ids:
            raise UserError("Please add at least one cutting line.")

        total_length = 0.0
        total_pieces = 0

        vals_list = []

        for line in self.line_ids:
            if line.no_of_piece <= 0:
                raise UserError("Pieces must be greater than 0.")

            if line.no_of_meter <= 0:
                raise UserError("Length must be greater than 0.")

            total_length += line.no_of_piece * line.no_of_meter
            total_pieces += line.no_of_piece

            vals_list.append({
                'sale_order_id': self.sale_order_id.id,
                'sale_order_line_id': self.sale_order_line_id.id,
                'product_id': self.product_id.id,
                'no_of_piece': line.no_of_piece,
                'no_of_meter': line.no_of_meter,
            })

        if total_length <= 0:
            raise UserError("Total length must be greater than 0.")

        # Remove old cutting lines for this sale order line
        self.sale_order_line_id.cutting_info_ids.unlink()

        # Create new cutting info lines
        self.env['cable.cutting.info'].create(vals_list)

        # Update main product sale order line quantity
        self.sale_order_line_id.write({
            'product_uom_qty': total_length,
        })

        # Create/update cable cutting charges line
        self.sale_order_id._sync_cable_cutting_charge_line()

        return {'type': 'ir.actions.act_window_close'}


class SaleOrderLineCableCuttingWizardLine(models.TransientModel):
    _name = 'sale.order.line.cable.cutting.wizard.line'
    _description = 'Sale Order Line Cable Cutting Wizard Line'

    wizard_id = fields.Many2one(
        'sale.order.line.cable.cutting.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )

    no_of_piece = fields.Integer(
        string='Pieces',
        required=True,
        default=1
    )

    no_of_meter = fields.Float(
        string='Length',
        required=True
    )

    total = fields.Float(
        string='Total',
        compute='_compute_total'
    )

    @api.depends('no_of_piece', 'no_of_meter')
    def _compute_total(self):
        for line in self:
            line.total = line.no_of_piece * line.no_of_meter

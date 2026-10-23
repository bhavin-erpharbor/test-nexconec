from odoo import models
from odoo.tools import format_date


class StockForecasted(models.AbstractModel):
    _inherit = 'stock.forecasted_product_product'

    def _prepare_report_line(
        self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False,
        reserved_move=False, in_transit=False, read=True
    ):
        line = super(StockForecasted, self)._prepare_report_line(
            quantity, move_out=move_out, move_in=move_in, replenishment_filled=replenishment_filled,
            product=product, reserved_move=reserved_move, in_transit=in_transit, read=read
        )
        # If entry is belongs to the purchase order, then display the PO's ETA date(date_planned) in forecast report.
        if move_in and move_in.purchase_line_id:
            purchase_order = move_in.purchase_line_id.order_id
            if purchase_order and purchase_order.date_planned:
                line.update({'receipt_date': format_date(self.env, purchase_order.x_studio_expected_arrival)})
        return line

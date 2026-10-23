from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    customer_product_category_id = fields.Many2one(
        "product.category",
        string="Customer Product Category",
        related="order_partner_id.product_category_id",
        readonly=True,
    )

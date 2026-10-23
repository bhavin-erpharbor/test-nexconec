from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    public_categ_ids = fields.Many2many("product.public.category", string="Categories")
    product_category_id = fields.Many2one('product.category', string="Category")

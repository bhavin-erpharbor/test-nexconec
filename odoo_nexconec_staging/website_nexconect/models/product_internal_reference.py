# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductInternalReference(models.Model):
    _name = 'product.internal.reference'
    _description = 'Product Internal Reference'

    name = fields.Char('Internal Reference')
    product_id = fields.Many2one('product.product', string="Product")

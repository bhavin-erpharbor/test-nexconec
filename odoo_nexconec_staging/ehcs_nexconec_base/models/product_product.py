from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_filtered_sellers(self, partner_id=False, quantity=0.0, date=None, uom_id=False, params=False):
        sellers = super()._get_filtered_sellers(partner_id=partner_id, quantity=quantity, date=date, uom_id=uom_id, params=params)
        if all(not seller.product_id for seller in sellers):
            return sellers
        return sellers.filtered(lambda s: s.product_id.id == self.id) if any(
            seller.product_id.id == self.id for seller in sellers) else sellers

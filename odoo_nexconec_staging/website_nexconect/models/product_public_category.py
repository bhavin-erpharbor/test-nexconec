# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.osv import expression


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    activate_subcategory_filter_using_customer = fields.Boolean(copy=False)

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        domain = domain or []

        # Apply only on website
        website_id = self.env.context.get('website_id')
        partner = self.env.user.partner_id

        if website_id and partner:
            public_categ_ids = partner.public_categ_ids.ids

            # Use parent company categories if available
            if partner.parent_id and partner.parent_id.public_categ_ids:
                public_categ_ids = partner.parent_id.public_categ_ids.ids

            if public_categ_ids:
                categ_domain = expression.OR([
                    [('id', 'in', public_categ_ids)],
                    [('id', 'parent_of', public_categ_ids)],
                ])

                domain = expression.AND([domain, categ_domain])

        return super().search_fetch(domain, offset=offset, limit=limit, order=order)

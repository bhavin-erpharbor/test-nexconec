from odoo import api, models
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        if self.env.context:
            website_id = self.env.context.get('website_id')
            if website_id and self.env.user.partner_id:
                partner = self.env.user.partner_id

                public_categ_ids = partner.public_categ_ids.ids
                if partner.parent_id and partner.parent_id.public_categ_ids:
                    public_categ_ids = partner.parent_id.public_categ_ids.ids

                extra_domain = [
                    ('public_categ_ids', 'in', public_categ_ids),
                    ('is_published', '=', True),
                ]

                domain = expression.AND([domain, extra_domain])

        return super(ProductProduct, self.sudo()).search_fetch(
            domain, [], offset=offset, limit=limit, order=order
        )

    def compute_location_qty_ids(self):
        """
        Compute product quantity by location
        """
        Quant = self.env['stock.quant']
        Warehouse = self.env['stock.warehouse']
        Location = self.env['stock.location']

        warehouses = Warehouse.sudo().search([])
        stock = []

        for warehouse in warehouses:
            line_vals = {'warehouse': warehouse.name}

            search_locations = Location.browse(
                warehouse.view_location_id.id)

            for product in self:
                lines = []
    
                for location in search_locations:
                    quants = Quant.sudo().search([
                        ('product_id', '=', product.id),
                        ('location_id', 'child_of', location.id)])
                    quntity_available = Quant.sudo()._get_available_quantity(product, location)
                    available_qty = sum(quants.mapped('available_quantity'))
                    reserved_qty = sum(quants.mapped('reserved_quantity'))
                    qty = available_qty - reserved_qty
                    virtual_qties = product.with_context(
                        warehouse=warehouse.id,
                    ).read(['virtual_available'])
                    total_virtual_qty = 0
                    for virtual_qty in virtual_qties:
                        total_virtual_qty = total_virtual_qty + virtual_qty.get('virtual_available', 0)
                    forecasted_qty = total_virtual_qty # sum(product.mapped('virtual_available'))

                    line_vals.update({'product_tmpl_id': product.id,
                                 'location':  location.name,
                                 'qty': quntity_available or 0,
                                 'forecasted_qty': forecasted_qty or 0,
                                 'product_uom_id': product.sudo().uom_id.id,
                                 'product_uom': product.sudo().uom_id.name})
                    stock.append(line_vals)
        return stock
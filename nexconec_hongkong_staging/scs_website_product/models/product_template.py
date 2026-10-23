# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = 'product.template'

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

        return super(ProductTemplate, self.sudo()).search_fetch(
            domain, [], offset=offset, limit=limit, order=order
        )

    def _get_combination_info(
            self, combination=False, product_id=False, add_qty=1.0, uom_id=False,
            only_template=False, custom_val=False, context=None, custom_pricelist=None
    ):
        combination_info = super(ProductTemplate, self)._get_combination_info(combination, product_id,add_qty, uom_id=uom_id, only_template=only_template)
        combination = combination or self.env['product.template.attribute.value']
        if not product_id and not combination and not only_template:
            combination = self._get_first_possible_combination()
        internal_code = ''
        
        if only_template:
            product = self.env['product.product']
        elif product_id:
            product = self.env['product.product'].browse(product_id)
            if (combination - product.product_template_attribute_value_ids):
                # If the combination is not fully represented in the given product
                #   make sure to fetch the right product for the given combination
                product = self._get_variant_for_combination(combination)
        else:
            product = self._get_variant_for_combination(combination)
            
        if combination_info and combination_info.get('product_id', product_id):
            product = self.env['product.product'].browse(product_id)
            if product:
                calculator_price = 1 #len(product.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.custom_cal == True))
                custom_attris = [] #product.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.is_custom_attribute == True)
                custom_vals = len(custom_attris)
                internal_code = product.get_internal_ref(custom_val, combination=combination)
                if calculator_price <= 0:
                    internal_code = product.default_code or product.product_tmpl_id.default_code or ''
            combination_info.update({
                'stock_by_location': product.sudo().compute_location_qty_ids(),
            })
        else:
            product_or_template = product or self
            price_context = product_or_template._get_product_price_context(combination)
            product_template = product_or_template.with_context(**price_context)
            product_template = product_template.with_context(current_attributes_price_extra=[v.price_extra or 0.0 for v in combination])
            first_product = product_template.product_variant_id
            if first_product and not combination:
                internal_code = first_product.get_internal_ref(custom_val, combination=combination)
            else:
                generated_code = ""
                if product_template.default_code:
                    generated_code += " " + self.default_code
                else:
                    pass
                for attri in combination:
                    if attri.attribute_id.is_custom_attribute:
                        val = float(custom_val) if custom_val else attri.custom_value
                        generated_code += '{0:g}'.format(val)
                    elif attri.ref_code:
                        generated_code += attri.ref_code
                    else:
                        pass
                internal_code = generated_code
        combination_info.update({
            'internal_code': internal_code,
        })
        return combination_info

    def compute_location_qty_ids(self):
        """
        Compute product quantity by location (sum of all variants)
        """
        stock_quant_ids = fields.One2many('stock.quant', compute='_compute_stock_quant_ids', string='Stock Quants')
        Quant = self.env['stock.quant']
        Warehouse = self.env['stock.warehouse']
        Location = self.env['stock.location']
        ProductProduct = self.env['product.product']

        warehouses = Warehouse.sudo().search([])
        stock = []

        for warehouse in warehouses:
            line_vals = {'warehouse': warehouse.name}
            search_locations = Location.browse(warehouse.view_location_id.id)

            for product in self:
                product_variant_ids = ProductProduct.search([
                    ('product_tmpl_id', '=', product.id)]).ids
                product.stock_quant_ids = product.product_variant_ids.mapped('stock_quant_ids')
    
                for location in search_locations:
                    query = [('location_id', 'child_of', location.id)]
                    if product_variant_ids:
                        query.append(('product_id', 'in', product_variant_ids))
                    else:
                        query.append(('product_id', '=', product.id))
    
                    quants = Quant.sudo().search(query)
                    available_qty = sum(quants.mapped('available_quantity'))
                    reserved_qty = sum(quants.mapped('reserved_quantity'))
                    qty = available_qty - reserved_qty
                    forecasted_qty = sum(quants.mapped('virtual_available'))
    
                    line_vals.update({'product_tmpl_id': product.id,
                                 'location':  location.name,
                                 'forecasted': forecasted_qty or 0,
                                 'qty': qty or 0,
                                 'product_uom_id': product.sudo().uom_id.id,
                                 'product_uom': product.sudo().uom_id.name})
                    stock.append(line_vals)
        return stock

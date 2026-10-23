# -*- coding: utf-8 -*-
import itertools
from odoo import api, fields, models, tools, _
from odoo.http import request
from odoo.osv import expression


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    custom_cal = fields.Boolean('Enable Calculator Price')
    is_custom_attribute = fields.Boolean('Custom Variable Attribute')
    is_connector = fields.Boolean()
    is_fiber_count = fields.Boolean()


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    custom_value = fields.Float('Custom Value')
    ref_code = fields.Char('Internal Code')
    no_varient_price = fields.Float('Price', help="price for 1 meter length")


class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    custom_value = fields.Float('Custom Value', related="product_attribute_value_id.custom_value")
    ref_code = fields.Char('Internal Code', related="product_attribute_value_id.ref_code")
#     price = fields.Float('Price', related="product_attribute_value_id.price")

    # def _only_active(self):
    #     active_ids = []
    #     if self._context:
    #         website_id = self._context.get('website_id', False)
    #         if website_id:
    #             if self.env.user.partner_id and self.env.user.partner_id.public_categ_ids:
    #                 cpublic_categ_ids = self.env.user.partner_id.public_categ_ids.ids
    #                 if cpublic_categ_ids:
    #                     for pro_temp_attr_value in self:
    #                         for product_variant in pro_temp_attr_value.ptav_product_variant_ids:
    #                             for public_categ_id in product_variant.public_categ_ids:
    #                                 if public_categ_id.id in cpublic_categ_ids:
    #                                     active_ids.append(pro_temp_attr_value.id)
    #                     if active_ids:
    #                         return self.filtered(lambda ptav: ptav.ptav_active and ptav.id in active_ids)
    #     return self.filtered(lambda ptav: ptav.ptav_active)

    # def get_price(self, combination, custom_val):
    #     calculator_price = len(combination.filtered(lambda l: l.attribute_id.custom_cal == True))
    #     custom_attris = combination.filtered(lambda l: l.attribute_id.is_custom_attribute == True)
    #     custom_vals = len(custom_attris)
    #     fiber_counts = len(combination.filtered(lambda l: l.attribute_id.is_fiber_count == True))
    #     connectors = len(combination.filtered(lambda l: l.attribute_id.is_connector == True))
    #     # we have a list of price_extra that comes from the attribute values, we need to sum all that
    #     extra_price = 0.0
    #     if calculator_price > 0 and custom_vals > 0:
    #         fiber_val = sum(combination.filtered(lambda l: l.attribute_id.is_fiber_count == True).mapped('custom_value'))
    #         custom_attri_vals = sum(custom_attris.mapped('custom_value'))
    #         if custom_val:
    #             custom_attri_vals = float(custom_val)
    #         extra_price = 0.0
    #         for attri in combination:
    #             if attri.attribute_id.is_connector:
    #                 extra_price += attri.product_attribute_value_id.no_varient_price * fiber_val
    #             elif attri.attribute_id.is_fiber_count and not attri.attribute_id.is_custom_attribute:
    #                 extra_price += attri.product_attribute_value_id.no_varient_price * custom_attri_vals
    #             elif attri.attribute_id.is_custom_attribute:
    #                 if fiber_counts < 1 and connectors < 1:
    #                     extra_price += attri.product_attribute_value_id.no_varient_price * custom_attri_vals
    #                 else:
    #                     pass
    #             else:
    #                 extra_price += attri.product_attribute_value_id.no_varient_price
    #     return extra_price

    def name_get(self):
        """Override because in general the name of the value is confusing if it
        is displayed without the name of the corresponding attribute.
        Eg. on exclusion rules form
        """
        lst = []
        for value in self:
            if value.attribute_id.is_custom_attribute and value.is_custom:
                lst.append((value.id, "%s" % (value.attribute_id.name)))
            else:
                lst.append((value.id, "%s: %s" % (value.attribute_id.name, value.name)))
        return lst

class ProductAttributeCustomValue(models.Model):
    _inherit = "product.attribute.custom.value"

    @api.depends('custom_product_template_attribute_value_id.name', 'custom_value')
    def _compute_name(self):
        for record in self:
            name = (record.custom_value or '').strip()
            if record.custom_product_template_attribute_value_id.display_name:
                name = "%s: %s" % (record.custom_product_template_attribute_value_id.display_name, name)
                if record.custom_product_template_attribute_value_id.attribute_id.is_custom_attribute:
                    name += 'mtr'
            record.name = name


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    minimum_qty = fields.Float('Minimum Quantity')
    allow_cable_cutting = fields.Boolean('Allow Cable Cutting')

    # stock_quant_ids = fields.One2many('stock.quant', compute='_compute_stock_quant_ids', string='Stock Quants')
    
    #@tools.ormcache('self.id', 'frozenset(filtered_combination.ids)')
    @tools.ormcache('self.id', 'frozenset(filtered_combination.ids)')
    def _get_variant_id_for_combination(self, filtered_combination):
        """See `_get_variant_for_combination`. This method returns an ID
        so it can be cached.

        Use sudo because the same result should be cached for all users.
        """
        self.ensure_one()
        domain = [('product_tmpl_id', '=', self.id)]
        combination_indices_ids = filtered_combination._ids2str()

        if combination_indices_ids:
            domain = expression.AND([domain, [('combination_indices', '=', combination_indices_ids)]])
        else:
            domain = expression.AND([domain, [('combination_indices', 'in', ['', False])]])

        return self.env['product.product'].sudo().with_context(active_test=False).search(domain, order='active DESC', limit=1).id

    @api.depends('product_variant_ids', 'product_variant_ids.default_code')
    def _compute_default_code(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.default_code = template.product_variant_ids.default_code
        # for template in (self - unique_variants):
        #     template.default_code = False

    # @api.model
    # harsh sir ne dekhadvanu
    # def search(self, domain, offset=0, limit=None, order=None):
    #     if self._context:
    #         website_id = self._context.get('website_id', False)
    #         print("\n\nwesiteid:::::", website_id, domain)
    #         if website_id:
    #             if self.env.user.partner_id:
    #                 public_categ_ids = self.env.user.partner_id.public_categ_ids.ids
    #                 if self.env.user.partner_id.parent_id and self.env.user.partner_id.parent_id.public_categ_ids:
    #                     public_categ_ids = self.env.user.partner_id.parent_id.public_categ_ids.ids
    #                 if domain:
    #                     domain.append(('public_categ_ids','in', public_categ_ids))
    #                     domain.append(('is_published','=', True))
    #                 else:
    #                     domain = [('public_categ_ids','in', public_categ_ids),('is_published','=', True)]
    #     return super(ProductTemplate, self.sudo()).search_fetch(domain, [], offset=offset, limit=limit, order=order)

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

    # def compute_location_qty_ids(self):
    #     """
    #     Compute product quantity by location
    #     """
    #     Quant = self.env['stock.quant']
    #     Warehouse = self.env['stock.warehouse']
    #     Location = self.env['stock.location']
    #     ProductProduct = self.env['product.product']

    #     warehouses = Warehouse.sudo().search([])
    #     stock = []

    #     for warehouse in warehouses:
    #         line_vals = {'warehouse': warehouse.name}
    #         search_locations = Location.browse(warehouse.view_location_id.id)

    #         for product in self:
    #             product_variant_ids = ProductProduct.search([
    #                 ('product_tmpl_id', '=', product.id)]).ids
    #             product.stock_quant_ids = product.product_variant_ids.mapped('stock_quant_ids')
    
    #             for location in search_locations:
    #                 query = [('location_id', 'child_of', location.id)]
    #                 if product_variant_ids:
    #                     query.append(('product_id', 'in', product_variant_ids))
    #                 else:
    #                     query.append(('product_id', '=', product.id))
    #                 quants = Quant.sudo().search(query)
    #                 available_qty = sum(quants.mapped('available_quantity'))
    #                 reserved_qty = sum(quants.mapped('reserved_quantity'))
    #                 qty = available_qty - reserved_qty
    #                 forecasted_qty = sum(quants.mapped('virtual_available'))
    
    #                 line_vals.update({'product_tmpl_id': product.id,
    #                             'location':  location.name,
    #                             'forecasted': forecasted_qty or 0,
    #                             'qty': qty or 0,
    #                             'product_uom_id': product.sudo().uom_id.id,
    #                             'product_uom': product.sudo().uom_id.name})
    #                 stock.append(line_vals)
    #     return stock


    def _create_variant_ids(self):
        if not self:
            return
        self.env.flush_all()
        Product = self.env["product.product"]

        variants_to_create = []
        variants_to_activate = Product
        variants_to_unlink = Product

        for tmpl_id in self:
            lines_without_no_variants = tmpl_id.valid_product_template_attribute_line_ids._without_no_variant_attributes()

            all_variants = tmpl_id.with_context(active_test=False).product_variant_ids.sorted(lambda p: (p.active, -p.id))

            current_variants_to_create = []
            current_variants_to_activate = Product

            # adding an attribute with only one value should not recreate product
            # write this attribute on every product to make sure we don't lose them
            single_value_lines = lines_without_no_variants.filtered(lambda ptal: len(ptal.product_template_value_ids._only_active()) == 1)
            if single_value_lines:
                for variant in all_variants:
                    combination = variant.product_template_attribute_value_ids | single_value_lines.product_template_value_ids._only_active()
                    # Do not add single value if the resulting combination would
                    # be invalid anyway.
                    if (
                        len(combination) == len(lines_without_no_variants) and
                        combination.attribute_line_id == lines_without_no_variants
                    ):
                        variant.product_template_attribute_value_ids = combination

            # Set containing existing `product.template.attribute.value` combination
            existing_variants = {
                variant.product_template_attribute_value_ids: variant for variant in all_variants
            }

            # Determine which product variants need to be created based on the attribute
            # configuration. If any attribute is set to generate variants dynamically, skip the
            # process.
            # Technical note: if there is no attribute, a variant is still created because
            # 'not any([])' and 'set([]) not in set([])' are True.
            if not tmpl_id.has_dynamic_attributes():
                # Iterator containing all possible `product.template.attribute.value` combination
                # The iterator is used to avoid MemoryError in case of a huge number of combination.
                all_combinations = itertools.product(*[
                    ptal.product_template_value_ids._only_active() for ptal in lines_without_no_variants
                ])
                # For each possible variant, create if it doesn't exist yet.
                for combination_tuple in all_combinations:
                    combination = self.env['product.template.attribute.value'].concat(*combination_tuple)
                    is_combination_possible = tmpl_id._is_combination_possible_by_config(combination, ignore_no_variant=True)
                    if not is_combination_possible:
                        continue
                    if combination in existing_variants:
                        current_variants_to_activate += existing_variants[combination]
                    else:
                        current_variants_to_create.append(tmpl_id._prepare_variant_values(combination))
                        variant_limit = self.env['ir.config_parameter'].sudo().get_param('product.dynamic_variant_limit', 50000)
                        if len(current_variants_to_create) > int(variant_limit):
                            raise UserError(_(
                                'The number of variants to generate is above allowed limit. '
                                'You should either not generate variants for each combination or generate them on demand from the sales order. '
                                'To do so, open the form view of attributes and change the mode of *Create Variants*.'))
                variants_to_create += current_variants_to_create
                variants_to_activate += current_variants_to_activate

            else:
                for variant in existing_variants.values():
                    is_combination_possible = self._is_combination_possible_by_config(
                        combination=variant.product_template_attribute_value_ids,
                        ignore_no_variant=True,
                    )
                    if is_combination_possible:
                        current_variants_to_activate += variant
                variants_to_activate += current_variants_to_activate

            variants_to_unlink += all_variants - current_variants_to_activate

        if variants_to_activate:
            variants_to_activate.write({'active': True})
        if variants_to_create:
            Product.create(variants_to_create)
        if variants_to_unlink:
            variants_to_unlink._unlink_or_archive()
            # prevent change if exclusion deleted template by deleting last variant

        # prefetched o2m have to be reloaded (because of active_test)
        # (eg. product.template: product_variant_ids)
        # We can't rely on existing invalidate because of the savepoint
        # in _unlink_or_archive.
        self.env.flush_all()
        self.env.invalidate_all()
        return True

    def _get_combination_info(
        self, combination=False, product_id=False, add_qty=1.0, uom_id=False,
        only_template=False,custom_val=False,context=None,custom_pricelist=None
    ):
        self.ensure_one()
        combination = combination or self.env['product.template.attribute.value']

        if 'pricelist' not in dir(request) and context.get('pricelist'):
            request.pricelist = context.get('pricelist')
        if 'fiscal_position' not in dir(request) and context.get('fiscalposition'):
            request.fiscal_position = context.get('fiscalposition')

        # website = request.website.with_context(self.env.context)
        website = self.env['website'].get_current_website()
        if custom_pricelist:
            pricelist = self.env['product.pricelist'].browse(custom_pricelist)
        else:
            current_website = self.env['website'].get_current_website()
            pricelist = context.get('pricelist') if context else False
            # pricelist = context.get('pricelist') if context else False  or current_website._get_current_pricelist()
            # not exist _get_current_pricelist() in odoo 19
        # current_website._get_current_pricelist()
        quantity = self.env.context.get('quantity', add_qty)
        context = dict(self.env.context, quantity=quantity, pricelist=pricelist.id if pricelist else False)
        product_template = self.with_context(context)


        if not product_id and not combination and not only_template:
            combination = self._get_first_possible_combination()

        if only_template:
            product = self.env['product.product']
        elif product_id and not combination:
            product = product_template.env['product.product'].browse(product_id)
        else:
            product = self._get_variant_for_combination(combination)
        product_or_template = product or self

        combination = combination or product.product_template_attribute_value_ids
        display_name = product_or_template.with_context(display_default_code=False).display_name
        if not product:
            combination_name = combination._get_combination_name()
            if combination_name:
                display_name = f"{display_name} ({combination_name})"

        price_context = product_or_template.with_context(custom_val=custom_val)._get_product_price_context(combination)
        product_or_template = product_or_template.with_context(**price_context)
        calculator_price = len(product.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.custom_cal == True))
        custom_attris = product.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.is_custom_attribute == True)
        internal_code = product.get_internal_ref(custom_val, combination=combination)
        if calculator_price <= 0:
            internal_code = product_or_template.default_code or product_or_template.product_variant_id.default_code or ''
        oproduct = product
        if internal_code:
            sinternal_code = internal_code
            #sinternal_code = ''.join(sorted(sinternal_code))
            oproduct = self.env['product.product'].sudo().search([
                "|", ('custom_internal_reference_no_sort', '=', sinternal_code),
                ('product_internal_reference_ids.name', '=', sinternal_code.strip()),
                ('id', '!=', product.id)
            ], limit = 1)
            if oproduct.qty_available <= 0:
                oproduct = False
        if not oproduct:
            oproduct = product
        product = oproduct
        uom = self.env['uom.uom'].browse(uom_id) or self.uom_id
        combination_info = {
            'combination': combination,
            'product_id': product.id,
            'product_template_id': self.id,
            'display_name': display_name,
            'is_combination_possible': self._is_combination_possible(combination=combination),
            'internal_code': internal_code,

            **self.with_context(combination=combination,internal_code=internal_code,pricelist=pricelist).sudo()._get_additionnal_combination_info(
                product_or_template=product_or_template,
                quantity=add_qty or 1.0,
                uom=uom,
                date=fields.Date.context_today(self),
                website=website,
                custom_val=custom_val,
            )

        }
        if website.google_analytics_key:
            combination_info['product_tracking_info'] = self._get_google_analytics_data(
                product,
                combination_info,
            )

        if (
                product_or_template.type == 'combo'
                and website.show_line_subtotals_tax_selection == 'tax_included'
                and not all(
            tax.price_include
            for tax
            in product_or_template.sudo().combo_ids.combo_item_ids.product_id.taxes_id
        )
        ):
            combination_info['tax_disclaimer'] = _(
                "Final price may vary based on selection. Tax will be calculated at checkout."
            )
        return combination_info


    def _get_additionnal_combination_info(self, product_or_template, quantity, uom, date, website, custom_val=False):
        res = super()._get_additionnal_combination_info(product_or_template, quantity, uom, date, website)
        # pricelist = website.pricelist_id
        pricelist = self.env.context.get('pricelist') or request.pricelist.with_context(self.env.context)
        #check if the model is product or product_template
        if product_or_template._table == "product_template":
            product = product_or_template.product_variant_ids[0]
        else:
            product = product_or_template
        currency = website.currency_id
        res['list_price'] = product_or_template._price_compute('list_price', custom_val=custom_val)[product_or_template.id]
        if pricelist and pricelist.currency_id != product_or_template.currency_id:
                res['list_price'] = product_or_template.currency_id._convert(
                        res['list_price'], pricelist.currency_id, self.env.user.company_id, fields.Date.today())
        first_product = product 
        p1 = first_product.with_context(custom_val=custom_val)._get_product_price(pricelist,res['list_price'], quantity,product_or_template.id)
        pricelist_price = pricelist._get_product_price(
            product=product_or_template,
            quantity=quantity,
            target_currency=currency,
        )
        res['price'] = p1[first_product.id] if pricelist else res['list_price'] or pricelist_price
        res['price_reduce'] = p1[first_product.id] if pricelist else res['list_price']
        internal_code = self.env.context.get('internal_code')
        # if calculator_price <= 0:
        #     internal_code = product_or_template.default_code or product_or_template.product_variant_id.default_code or ''

        oproduct = product
        if internal_code:
            sinternal_code = internal_code
            #sinternal_code = ''.join(sorted(sinternal_code))
            oproduct = self.env['product.product'].sudo().search([
                "|", ('custom_internal_reference_no_sort', '=', sinternal_code),
                ('product_internal_reference_ids.name', '=', sinternal_code.strip()),
                ('id', '!=', product.id)
            ], limit = 1)
            if oproduct.qty_available <= 0:
                oproduct = False
        if not oproduct:
            oproduct = product
        product = oproduct
        if product_or_template:
            website = self.env['website'].get_current_website()
            virtual_available = product.with_context(warehouse=website.warehouse_id.id).sudo().virtual_available
            res.update({
                'virtual_available': virtual_available,
                'virtual_available_formatted': self.env['ir.qweb.field.float'].value_to_html(virtual_available, {'precision': 0}),
                'product_type': product.type,
                'allow_cable_cutting': product.allow_cable_cutting,
                # 'inventory_availability': product.inventory_availability,
                'available_threshold': product.available_threshold,
                # 'custom_message': product.custom_message,
                'product_template': product.id,
                'cart_qty': product.qty_available,
                'uom_name': product.uom_id.name,
                'stock_by_location': product.sudo().compute_location_qty_ids(),
                'display_manufacture_status': product.sudo().check_mf_status(),
                'calculate_available_products': product.sudo().calculate_available_products(),
                # 'price': price,
                # 'list_price': list_price,
            })

        else:
            product_template = self.sudo()
            res.update({
                'virtual_available': 0,
                'product_type': product_template.type,
                'allow_cable_cutting': product.allow_cable_cutting,
                # 'inventory_availability': product_template.inventory_availability,
                'available_threshold': product_template.available_threshold,
                # 'custom_message': product_template.custom_message,
                'product_template': product_template.id,
                'cart_qty': 0
            })
        return res

    def compute_available_pricelist(self, pricelist):
        pricelist_item_obj = self.env['product.pricelist.item']
        rule_list = []

        for product_template in self:
            all_rules = pricelist._get_applicable_rules(product_template, fields.Date.today())
            valid_rules = all_rules.filtered(lambda r: r.min_quantity > 0)
            for rule in valid_rules:
                price = rule._compute_price(product_template, rule.min_quantity, product_template.uom_id, fields.Date.today())
                rule_data = {
                    'min_quantity': rule.min_quantity,
                    'price': price,
                    'uom': rule.product_id.sudo().uom_id.name if rule.product_id else rule.product_tmpl_id.sudo().uom_id.name,
                    'cur_name': rule.currency_id and rule.currency_id.symbol
                }
                rule_list.append(rule_data)
        return rule_list

    def _price_compute(self, price_type, uom=None, currency=None, company=None, custom_val=False, date=False):
        pid = self.env.context.get('pid')
        company = company or self.env.company
        date = date or fields.Date.context_today(self)
        custom_price = self.env.context.get('custom_price')
        self = self.with_company(company)
        if price_type == 'standard_price':
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            self = self.sudo()

        prices = dict.fromkeys(self.ids, 0.0)
        for template in self:
            price = template[price_type] or 0.0
            price_currency = template.currency_id
            first_product = template.product_variant_id
            calculator_price = len(first_product.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.custom_cal == True))
            custom_attris = first_product.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.is_custom_attribute == True)
            custom_vals = len(custom_attris)
            fiber_counts = len(first_product.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.is_fiber_count == True))
            connectors = len(first_product.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.is_connector == True))
            prices[template.id] = template[price_type] or 0.0
            if price_type == 'standard_price':
                if not price and template.product_variant_ids:
                    price = template.product_variant_ids[0].standard_price
                price_currency = template.cost_currency_id
            elif price_type == 'list_price':
                    if calculator_price > 0 and custom_vals > 0:
                        fiber_val = sum(first_product.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.is_fiber_count == True).mapped('custom_value'))
                        custom_attri_vals = sum(custom_attris.mapped('custom_value'))
                        if custom_val:
                            custom_attri_vals = float(custom_val)
                        extra_price = 0.0
                        for attri in first_product.product_template_attribute_value_ids:
                            if attri.attribute_id.is_connector:
                                extra_price += attri.price_extra * fiber_val
                            elif attri.attribute_id.is_fiber_count and not attri.attribute_id.is_custom_attribute:
                                extra_price += attri.price_extra * custom_attri_vals
                            elif attri.attribute_id.is_custom_attribute:
                                if fiber_counts < 1 and connectors < 1:
                                    extra_price += attri.price_extra * custom_attri_vals
                                else:
                                    pass
                            else:
                                extra_price += attri.price_extra
                        prices[template.id] += extra_price
                    else:
                        prices[template.id] += first_product._get_attributes_extra_price()

            if uom:
                prices[template.id] = template.uom_id._compute_price(price, uom)

            # Convert from current user company currency to asked one
            # This is right cause a field cannot be in more than one currency
            if currency:
                prices[template.id] = price_currency._convert(prices[template.id], currency, company, date)
        if custom_price:
            prices[pid]= custom_price
        return prices

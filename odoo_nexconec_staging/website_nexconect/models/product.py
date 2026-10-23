from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # stock_quant_ids = fields.One2many('stock.quant', compute='_compute_stock_quant_ids', string='Stock Quants')
    
    def convert_image_to_jpeg_base64(self, datas):
        """
        Get the image data in jpeg format.
        """
        try:
            data_uri = self.env['ir.qweb'].with_context(webp_as_jpg=True)._get_converted_image_data_uri(datas)
            _header, base64_data = data_uri.split('base64,', 1)
            return base64_data
        except TypeError:
            return datas

    def calculate_available_products(self):
        quant_obj = self.env['stock.quant']
        for product in self:
            available_products = float('0')  # Start with an arbitrarily large number

            # Iterate through all BOMs of the product
            for bom in product.bom_ids:
                for line in bom.bom_line_ids:
                    # Calculate the number of finished products that can be produced for this component
                    component_qty_required = line.product_qty
                    component_stock = quant_obj.search([
                        ('location_id.usage', '=', 'internal'),
                        ('product_id', '=', line.product_id.id)
                    ])

                    # Ensure there is stock to calculate the production capacity
                    if component_qty_required > 0:
                        max_products_for_component = component_stock.available_quantity // component_qty_required
                    else:
                        max_products_for_component = 0

                    # Update the available products with the limiting component
                    available_products = min(available_products, max_products_for_component)

            return available_products

    def check_mf_status(self):
        # Accessing the mrp.bom model to search for BOMs (Bills of Materials)
        quant_obj = self.env['stock.quant']

        # Looping through the current products
        for product in self:
            # Iterate through all BOMs of the product
            for bom in product.bom_ids:
                for bom_line in bom.bom_line_ids:
                    product = bom_line.product_id
                    quant = quant_obj.search([
                        ('location_id.usage', '=', 'internal'),
                        ('product_id', '=', product.id)
                    ])
                    if quant and quant.available_quantity <= 0:
                        return False

                # If all BOM lines have stock available, return True
                return True

        # If no BOM is found for the product, return False by default
        return False

    def compute_location_qty_ids(self):
        """
        Compute product quantity by warehouse/location with lot-wise accuracy
        """
        Quant = self.env['stock.quant'].sudo()
        Warehouse = self.env['stock.warehouse'].sudo()

        warehouses = Warehouse.search([])
        stock = []

        for product in self:
            for warehouse in warehouses:

                # Main stock location of warehouse
                location = warehouse.view_location_id

                # Get all quants for this product under this warehouse
                quants = Quant.search([
                    ('product_id', '=', product.id),
                    ('location_id', 'child_of', location.id)
                ])

                # Forecasted qty (warehouse-wise)
                forecasted_qty = product.with_context(
                    warehouse=warehouse.id
                ).virtual_available

                base_line = {
                    'warehouse': warehouse.name,
                    'product_tmpl_id': product.id,
                    'location': location.name,
                    'forecasted_qty': forecasted_qty or 0,
                    'product_uom_id': product.uom_id.id,
                    'product_uom': product.uom_id.name,
                }

                # -----------------------------
                # LOT-WISE HANDLING
                # -----------------------------
                lot_quants = quants.filtered(lambda q: q.lot_id)

                if lot_quants:
                    # Group quantities by lot
                    lot_map = {}

                    for quant in lot_quants:
                        lot_name = quant.lot_id.name
                        available_qty = quant.available_quantity

                        # Skip zero/negative stock
                        if available_qty <= 0:
                            continue

                        if lot_name not in lot_map:
                            lot_map[lot_name] = 0

                        lot_map[lot_name] += available_qty

                    # Append each lot separately
                    for lot_name, qty in lot_map.items():
                        stock.append({
                            **base_line,
                            'lot_id': lot_name,
                            'qty': qty,
                        })

                else:
                    # -----------------------------
                    # NO LOT CASE
                    # -----------------------------
                    total_available = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))

                    if total_available > 0:
                        stock.append({
                            **base_line,
                            'lot_id': False,
                            'qty': total_available,
                        })
        return stock


    def get_internal_ref(self, custom_val=False, combination=False):
        generated_code = ""
        if not combination:
            combination = self.product_template_attribute_value_ids
        calculator_price = len(combination.filtered(lambda l: l.attribute_id.custom_cal == True))
        if self.default_code:
            generated_code += " " + self.default_code
        elif self.product_tmpl_id.default_code:
            generated_code += " " + self.product_tmpl_id.default_code
        else:
            pass
        if calculator_price > 0:
            for attri in combination:
                if attri.attribute_id.is_custom_attribute:
                    val = float(custom_val) if custom_val else attri.custom_value
                    generated_code += '{0:g}'.format(val)
                elif attri.ref_code:
                    generated_code += attri.ref_code
                else:
                    pass
        return generated_code


    def _get_product_price(self, pricelist, custom_price, qty,pid, **kwargs):
        prices = {}
        pricelist_id_or_name = [pricelist.name]
        if pricelist_id_or_name:
            pricelist = None
            partner = self.env.context.get('partner', False)
            quantity = qty

            # Support context pricelists specified as list, display_name or ID for compatibility
            if isinstance(pricelist_id_or_name, list):
                pricelist_id_or_name = pricelist_id_or_name[0]
            if isinstance(pricelist_id_or_name, str):
                pricelist_name_search = self.env['product.pricelist'].name_search(pricelist_id_or_name, operator='=', limit=1)
                if pricelist_name_search:
                    pricelist = self.env['product.pricelist'].browse([pricelist_name_search[0][0]])
            elif isinstance(pricelist_id_or_name, int):
                pricelist = self.env['product.pricelist'].browse(pricelist_id_or_name)

            if pricelist:
                quantities = quantity * len(self)
                # quantities = [quantity] * len(self)
                partners = [partner] * len(self)
                currency = self.env.company.currency_id
                prices = pricelist.with_context(custom_price=custom_price,pid=pid)._get_products_price(self, quantities, currency, partners, **kwargs)
        return prices

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
            calculator_price = len(template.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.custom_cal == True))
            custom_attris = template.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.is_custom_attribute == True)
            custom_vals = len(custom_attris)
            fiber_counts = len(template.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.is_fiber_count == True))
            connectors = len(template.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.is_connector == True))
            prices[template.id] = template[price_type] or 0.0
            if price_type == 'standard_price':
                if not price and template.product_variant_ids:
                    price = template.product_variant_ids[0].standard_price
            elif price_type == 'list_price':
                    if calculator_price > 0 and custom_vals > 0:
                        fiber_val = sum(template.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.is_fiber_count == True).mapped('custom_value'))
                        custom_attri_vals = sum(custom_attris.mapped('custom_value'))
                        if custom_val:
                            custom_attri_vals = float(custom_val)
                        extra_price = 0.0
                        for attri in template.product_template_attribute_value_ids:
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
                        prices[template.id] += template.price_extra
                        if self.env.context.get('no_variant_attributes_price_extra'):
                            extra_price = self._context.get('no_variant_attributes_price_extra', 0.0)
                            if isinstance(extra_price, (list, tuple)):
                                extra_price = sum(extra_price)

                            prices[template.id] += extra_price

            if uom:
                prices[template.id] = template.uom_id._compute_price(prices[template.id], uom)

            if currency:
                prices[template.id] = template.currency_id._convert(
                    prices[template.id], currency, template.company_id, fields.Date.today())
        if custom_price:
            prices[pid]= custom_price
        return prices

    # @api.depends('product_template_attribute_value_ids', 'default_code', 'product_tmpl_id.default_code')
    # def _get_custom_internal_reference(self):
    #     for product in self:
    #         calculator_price = len(product.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.custom_cal == True))
    #         custom_val = False
    #         internal_code = product.get_internal_ref(custom_val, combination=product.product_template_attribute_value_ids)
    #         if calculator_price <= 0:
    #             internal_code = product.default_code or product.product_tmpl_id.default_code or ''
    #         product.cust_internal_reference = ''.join(sorted(internal_code))

    @api.depends('product_template_attribute_value_ids', 'default_code', 'product_tmpl_id.default_code')
    def _get_custom_internal_reference_no_sort(self):
        for product in self:
            calculator_price = len(product.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.custom_cal == True))
            custom_val = False
            internal_code = product.get_internal_ref(custom_val, combination=product.product_template_attribute_value_ids)
            if calculator_price <= 0:
                internal_code = product.default_code or product.product_tmpl_id.default_code or ''
            product.custom_internal_reference_no_sort = internal_code


    # cust_internal_reference = fields.Char(compute="_get_custom_internal_reference", string="Custom Internal Reference", store = True)
    custom_internal_reference_no_sort = fields.Char(compute="_get_custom_internal_reference_no_sort", string="Custom Internal Reference", store = True)
    product_internal_reference_ids = fields.One2many('product.internal.reference', 'product_id', 'Multiple Reference')


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    partner_ids = fields.Many2many('res.partner', string='Customers')

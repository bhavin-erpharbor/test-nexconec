from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang
from odoo.tools.float_utils import float_round


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    x_studio_delivery_status = fields.Char(
        compute='compute_delivery_status', store=True, string='Delivery status')

    @api.model_create_multi
    def create(self, vals):
        res = super(PurchaseOrder, self).create(vals)
        if res and res.origin:
            order = self.env['sale.order'].search(
                [('name','=',res.origin.split(',')[-1].replace(" ", ""))], limit=1)
            dropship_route = self.env['stock.route'].sudo().search(
                [('name', '=', 'Dropship')], limit=1)
            dropship = False

            if any(route.id == dropship_route.id for line in order.order_line for route in line.route_ids):
                dropship = True

            if order and order.x_studio_delivery_contact_1 and dropship:
                res.sudo().write({
                    'x_studio_drop_ship_contact_1': order.x_studio_delivery_contact_1.id})
            if order and order.x_studio_delivery_message:
                res.sudo().write({
                    'x_studio_delivery_message': order.x_studio_delivery_message})
        return res

    def write(self, vals):
        if vals.get('origin'):
            order = self.env['sale.order'].search(
            [('name','=', vals.get('origin').split(',')[-1].replace(" ", ""))], limit=1)
            dropship_route = self.env['stock.route'].sudo().search(
            [('name', '=', 'Dropship')], limit=1)
            dropship = False

            if any(route.id == dropship_route.id for line in order.order_line for route in line.route_ids):
                dropship = True

            if order and order.x_studio_delivery_contact_1 and dropship:
                vals.update({
                    'x_studio_drop_ship_contact_1': order.x_studio_delivery_contact_1.id})
            if order and order.x_studio_delivery_message:
                vals.update({
                    'x_studio_delivery_message': order.x_studio_delivery_message})
        result = super(PurchaseOrder, self).write(vals)
        return result

    @api.depends('order_line.qty_received', 'order_line.product_qty', 'order_line.state')
    def compute_delivery_status(self):
        flag_rec_part = 0
        flag_rec = 0
        flag_not_rec = 0
        delivery_status = ''
        for order in self:
            total_line_count = len(order.order_line)
            service_count = 0
            for line in order.order_line.filtered(lambda l: l.state == 'purchase'):
                if line.product_id.type == 'service':
                    service_count = service_count + 1
                    continue
                if line.product_id.type == 'product':
                    if line.product_qty <= line.qty_received:
                        flag_rec = 1
                    elif line.product_qty > line.qty_received:
                        if line.qty_received != 0:
                            flag_rec_part = 1
                        else:
                            flag_not_rec = 1
                if flag_rec_part == 1:
                    delivery_status = 'Partially Delivered'
                elif flag_rec == 1 and flag_not_rec == 1:
                    delivery_status = 'Partially'
                elif flag_rec == 1 and flag_not_rec == 0:
                    delivery_status = 'Completed'
                elif (flag_rec == 0 and flag_not_rec == 0) or (flag_rec == 0 and flag_not_rec == 1):
                    delivery_status = 'In process'
            if service_count == total_line_count:
                delivery_status = 'Completed'
            order.write({'x_studio_delivery_status': delivery_status})

    def _prepare_invoice(self):
        """Prepare the dict of values to create the new invoice for a purchase order.
        """
        invoice_vals = super(PurchaseOrder, self)._prepare_invoice()
        today = fields.Date.context_today(self)
        invoice_vals.update({'invoice_date': today})
        return invoice_vals

    @api.depends('order_line.date_planned')
    def _compute_date_planned(self):
        """ date_planned = the earliest date_planned across all order lines. """
        for order in self:
            dates_list = order.order_line.filtered(lambda x: not x.display_type and x.date_planned).mapped('date_planned')
            if dates_list:
                order.date_planned = fields.Datetime.to_string(max(dates_list))
            else:
                order.date_planned = False


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values,
                                                      po):
        rec = super()._prepare_purchase_order_line_from_procurement(product_id, product_qty, product_uom, location_dest_id, name, origin,company_id,
                                                                    values, po)
        partner = po.partner_id
        product_lang = product_id.with_context(
            lang=partner.lang,
            partner_id=partner.id)

        if values.get('so_line_id') and not partner.is_without_product_attribute_description:
            line_description = values.get('so_line_id').with_context(
            partner_lang=partner.lang)._get_sale_order_line_multiline_description_sale()
            rec['name'] = _(line_description)
        # for dorpship type purchase order

        elif values.get('code_intern') and not partner.is_without_product_attribute_description:
            varient_description = values['product_description_variants']
            if values.get('so_line'):
                varient_description = values.get('so_line').with_context(
                    partner_lang=partner.lang
                    )._get_sale_order_line_multiline_description_variants()
            line_description = values.get('code_intern') + "\n" + product_lang.get_product_multiline_description_sale() + varient_description
            rec['name'] = _(line_description)

        elif values.get('so_line_id') and partner.is_without_product_attribute_description:

            line_description = values.get('so_line_id').with_context(partner_lang=partner.lang)\
                ._get_sale_order_line_multiline_description_sale_value()
            rec['name'] = _(line_description)
        return rec

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('order_id') and not vals.get('date_planned'):
                po = self.env['purchase.order'].browse(vals.get('order_id'))
                if po.state == 'purchase':
                    dates_list = po.order_line.filtered(lambda x: x.date_planned).mapped('date_planned')
                    if dates_list:
                        date_planned = fields.Datetime.to_string(max(dates_list))
                        vals.update({'date_planned': date_planned})
        return super(PurchaseOrderLine, self).create(vals_list)

    def _get_code_intern_description(self):
        combination = self.product_id.product_template_attribute_value_ids
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin
        custom_val = ""
        for attri in self.product_custom_attribute_value_ids:
            if attri.custom_product_template_attribute_value_id.attribute_id.is_custom_attribute:
                custom_val = attri.custom_value
        if no_variant_ptavs:
            combination += no_variant_ptavs
            ptavs = sorted(combination, key=lambda x: x.attribute_id.sequence)
            combo = []
            for attri in ptavs:
                combo.append(attri.id)
            combination = self.env['product.template.attribute.value'].browse(combo)
        refcode = 'Code intern:' + self.product_id.get_internal_ref(custom_val, combination=combination)
        return refcode

    def _get_variant_description_only_value(self):
        name = ""
        combination = self.product_id.product_template_attribute_value_ids
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin
        if no_variant_ptavs:
            combination += no_variant_ptavs
            ptavs = sorted(combination, key=lambda x: x.attribute_id.sequence)
            combo = []
            for attri in ptavs:
                combo.append(attri.id)
            combination = self.env['product.template.attribute.value'].browse(combo)
        # Collecting the attribute values in a list for display
        attributes = []
        lang = self.partner_id.lang
        if self.env.context.get('partner_lang'):
            lang = self.env.context.get('partner_lang')
        for attri in self.product_custom_attribute_value_ids:
            if attri.custom_product_template_attribute_value_id:
                combination -= attri.custom_product_template_attribute_value_id
        for ptav in combination:
            if ptav.id:
                attributes.append(ptav.with_context(lang=lang).product_attribute_value_id.name)
        for attri in self.product_custom_attribute_value_ids:
            if attri.custom_product_template_attribute_value_id:
                name += "\n" + "%s: %s" % (attri.with_context(lang=lang).custom_product_template_attribute_value_id.name, attri.with_context(lang=lang).custom_value)
                attributes.append(name)

        if attributes:
            name = f"({','.join(attributes)})"
        return name

    def _get_variant_description(self):
        combination = self.product_id.product_template_attribute_value_ids
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin
        if no_variant_ptavs:
            combination += no_variant_ptavs
            ptavs = sorted(combination, key=lambda x: x.attribute_id.sequence)
            combo = []
            for attri in ptavs:
                combo.append(attri.id)
            combination = self.env['product.template.attribute.value'].browse(combo)
        name = ""
        lang = self.partner_id.lang
        if self.env.context.get('partner_lang'):
            lang=self.env.context.get('partner_lang')
        for attri in self.product_custom_attribute_value_ids:
            if attri.custom_product_template_attribute_value_id:
                combination -= attri.custom_product_template_attribute_value_id
        for ptav in combination:
            if ptav.id :
                name += "\n" + ptav.with_context(lang=lang).display_name
        for attri in self.product_custom_attribute_value_ids:
            if attri.custom_product_template_attribute_value_id:
                name += "\n" + attri.with_context(lang=lang).display_name

        return name

    def _get_productPurchase_description(self, product_lang):
        self.ensure_one()
        name = product_lang.name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase
        return name

    def _product_id_change(self):
        if not self.product_id:
            return

        self.product_uom_id = self.product_id.uom_id
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=None,
            company_id=self.company_id.id,
        )
        lang = self.partner_id.lang
        if self.env.context.get('partner_lang'):
            lang=self.env.context.get('partner_lang')

        name = self.with_context(partner_lang=lang)._get_code_intern_description()
        name = name + "\n" + self._get_productPurchase_description(product_lang)
        if self.order_id.partner_id.is_without_product_attribute_description:
            name += self.with_context(partner_lang=lang)._get_variant_description_only_value() + "\n"
        else:
            name += self.with_context(partner_lang=lang)._get_variant_description()
        self.name = name + "\n"

        self._compute_tax_id()

    _CONFIGURATOR_VAL_KEYS = (
        'price_subtotal',
        'product_no_variant_attribute_value_ids',
        'product_custom_attribute_value_ids',
    )

    def _is_configurator(self, values=None):
        if values is not None:
            return any(key in values for key in self._CONFIGURATOR_VAL_KEYS)
        self.ensure_one()
        return bool(
            self.env.context.get('from_product_configurator')
            or self.product_no_variant_attribute_value_ids
            or self.product_custom_attribute_value_ids
            or (
                    self.technical_price_unit
                    and self.price_unit
                    and self.technical_price_unit != self.price_unit
            )
        )

    def _set_configurator_price(self, price_unit):
        self.price_unit = price_unit
        self.technical_price_unit = price_unit + 1.0
        self.discount = 0.0

    def _apply_configurator_pricing(self, qty=None):
        self.ensure_one()
        if qty is not None:
            self.product_qty = qty
        self._set_configurator_price(self._get_vendor_or_sales_price_unit())

    def _get_vendor_or_sales_price_unit(self):
        self.ensure_one()
        precision = max(
            self.currency_id.decimal_places,
            self.env['decimal.precision'].precision_get('Product Price'),
        )
        po_line_uom = self.product_uom_id or self.product_id.uom_id
        date = self.date_order or fields.Date.context_today(self)
        partner = self.order_id.partner_id.commercial_partner_id
        seller = self.product_id.seller_ids.filtered(
            lambda s: (
                    s.partner_id.commercial_partner_id == partner
                    and (not s.product_id or s.product_id == self.product_id)
                    and (not s.date_start or s.date_start <= date)
                    and (not s.date_end or s.date_end >= date)
            )
        ).sorted(lambda s: (s.sequence, s.id))[:1]

        if seller:
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                seller.price,
                self.product_id.supplier_taxes_id,
                self.tax_ids,
                self.company_id,
            )
            price_unit = seller.currency_id._convert(
                price_unit, self.currency_id, self.company_id, date, False,
            )
            price_unit = float_round(price_unit, precision_digits=precision)
            seller_uom = seller.product_uom_id or self.product_id.uom_id
            return seller_uom._compute_price(price_unit, self.product_uom_id)

        price_unit = self.product_id.uom_id._compute_price(self.product_id.lst_price, po_line_uom)
        price_unit = self.company_id.currency_id._convert(
            price_unit, self.currency_id, self.company_id, date, False,
        )
        return float_round(price_unit, precision_digits=precision)

    def _suggest_quantity(self):
        lines = self.filtered(lambda line: not (
                line._is_configurator() or (line.product_qty and line.price_unit)
        ))
        return super(PurchaseOrderLine, lines)._suggest_quantity()

    @api.model
    def _prepare_add_missing_fields(self, values):
        if not self._is_configurator(values):
            return super()._prepare_add_missing_fields(values)
        qty = values.get('product_qty')
        res = super(
            PurchaseOrderLine, self.with_context(from_product_configurator=True),
        )._prepare_add_missing_fields(values)
        if qty is not None:
            res['product_qty'] = qty
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('display_type', self.default_get(['display_type'])['display_type']):
                values.update({
                    'product_id': False,
                    'price_unit': 0,
                    'product_uom_qty': 0,
                    'product_uom_id': False,
                    'date_planned': False,
                })
                continue

            from_configurator = self._is_configurator(values)
            configurator_qty = values.get('product_qty') if from_configurator else None
            values.update(self._prepare_add_missing_fields(values))
            if from_configurator and configurator_qty is not None:
                values['product_qty'] = configurator_qty
            if values.get('price_unit') and not values.get('technical_price_unit'):
                values['technical_price_unit'] = (
                    values['price_unit'] + 1.0 if from_configurator else values['price_unit']
                )

        lines = super().create(vals_list)
        for line in lines.filtered(lambda l: l._is_configurator()):
            line._apply_configurator_pricing()

        for line in lines:
            if line.product_id and line.order_id.state == 'purchase':
                line.order_id.message_post(body=_("Extra line with %s ", line.product_id.display_name))

        return lines

    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id or (self.env.context.get('origin_po_id') and self.product_qty):
            return

        from_configurator = self._is_configurator() or bool(self.product_qty and self.price_unit)
        saved_qty = self.product_qty if from_configurator else 0.0

        if not from_configurator:
            self.price_unit = self.product_qty = self.technical_price_unit = 0.0

        self._product_id_change()

        if from_configurator:
            self._apply_configurator_pricing(saved_qty)
        else:
            self._suggest_quantity()

    @api.depends('product_qty', 'product_uom_id', 'company_id', 'order_id.partner_id')
    def _compute_price_unit_and_date_planned_and_name(self):
        configurator_qty = {}
        manual_prices = {}

        for line in self:
            if (
                    not line.product_id
                    or line.invoice_lines
                    or not line.company_id
                    or self.env.context.get('skip_uom_conversion')
            ):
                continue
            if line._is_configurator():
                configurator_qty[line.id] = line.product_qty
                line.technical_price_unit = line.price_unit
            elif line.technical_price_unit != line.price_unit:
                manual_prices[line.id] = (
                    line.price_unit, line.technical_price_unit, line.discount,
                )

        super()._compute_price_unit_and_date_planned_and_name()

        for line in self:
            if line.id in configurator_qty:
                line._apply_configurator_pricing(configurator_qty[line.id])
            elif line.id in manual_prices:
                line.price_unit, line.technical_price_unit, line.discount = manual_prices[line.id]
                if line.selected_seller_id or not line.date_planned:
                    line.date_planned = line._get_date_planned(
                        line.selected_seller_id,
                    ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

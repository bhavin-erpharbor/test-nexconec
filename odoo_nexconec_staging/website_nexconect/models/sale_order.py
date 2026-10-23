# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.http import request
import re
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    po_date_planned = fields.Date(string="Planned Delivery Date", compute='_compute_po_date_planned')
    save_from_cart = fields.Boolean()
    update_display_message_from_portal = fields.Boolean()
    cutting_info_ids = fields.One2many('cable.cutting.info', 'sale_order_id', string="Cutting Infos")

    @api.depends('order_line.purchase_line_ids.order_id.date_planned')
    def _compute_po_date_planned(self):
        for order in self:
            # Récupérer toutes les lignes de commande d'achat liées aux lignes de la commande de vente
            po_lines = order.order_line.mapped('purchase_line_ids')
            if po_lines:
                # Récupérer la première date planifiée parmi les PO liées
                order.po_date_planned = po_lines[0].order_id.date_planned
            else:
                order.po_date_planned = False

    # TODO: Name changed from onchange_partner_shipping_id to _compute_fiscal_position_id
    @api.depends('partner_shipping_id')
    def _compute_fiscal_position_id(self):
        res = super(SaleOrder, self)._compute_fiscal_position_id()
        if self.env.context.get('website_id', False):
            self.update({ 'x_studio_delivery_contact_1': self.partner_id })
        return res

    @api.model_create_multi
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if not self.env.context.get('website_id', False):
            if res.partner_id and res.partner_id.parent_id:
                res.partner_invoice_id = res.partner_id.parent_id.id
        elif res.partner_id and res.partner_id.parent_id and not res.partner_invoice_id.is_company:
            # Website : force la société en facturation si l'adresse actuelle
            # n'est pas déjà une adresse "société" valide.
            res.partner_invoice_id = res.partner_id.parent_id.id
        if not res.x_studio_delivery_contact_1:
            res.x_studio_delivery_contact_1 = res.partner_shipping_id
        return res

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        context = self.env.context
        if not context.get('website_id', False) and not context.get("company_invoice_id", False):
            for sale in self.filtered(lambda s: not s.website_id):
                if sale.partner_id and sale.partner_id.parent_id:
                    sale.with_context(company_invoice_id=True).write({
                        "partner_invoice_id": sale.partner_id.parent_id.id
                    })
        elif context.get('website_id', False) and not context.get("company_invoice_id", False):
            for sale in self.filtered(lambda s: s.website_id):
                if sale.partner_id and sale.partner_id.parent_id and not sale.partner_invoice_id.is_company:
                    sale.with_context(company_invoice_id=True).write({
                        "partner_invoice_id": sale.partner_id.parent_id.id
                    })
        return res

    # def action_confirm(self):
    #     for order in self:
    #         if order.x_studio_amount_due > order.x_studio_credit_limit:
    #             raise UserError(_("Credit limit overpassed"))
    #     res = super(SaleOrder, self).action_confirm()
    #     return res

    def cancel_draft_so(self):
        #Cancel Draft sale order of website
        current_website = self.env['website'].get_current_website()
        abandoned_delay = current_website and current_website.cart_abandoned_delay or False
        if abandoned_delay:
            abandoned_datetime = fields.Datetime.to_string(datetime.utcnow() - relativedelta(hours=abandoned_delay))
            so_ids = self.search([('state', '=', 'draft'),
                                  ('date_order', '<=', abandoned_datetime),
                                  ('website_id', '!=', False),])
            for order in so_ids:
                order.action_cancel()

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        res = super(SaleOrder, self)._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)
        if res.get('line_id'):
            OrderLine = self._cart_find_product_line(product_id, line_id, **kwargs)
        else:
            OrderLine = self.env['sale.order.line']
        if res.get('line_id') and res.get('quantity') > 0:
            order_line = OrderLine.browse(res.get('line_id'))
            combination = order_line.product_id.product_template_attribute_value_ids
            combo_price = order_line.product_id.product_tmpl_id._get_combination_info(combination, int(order_line.product_id.id or 0), int(order_line.product_uom_qty or 1), custom_val=order_line.custom_val)
            price = combo_price['price']
            order_line.write({'price_unit': price})
#             if order_line and order_line.product_id and order_line.custom_val > 0:
#                 list_price = order_line.product_id.price_compute('list_price', custom_val=order_line.custom_val)[order_line.product_id.id]
#                 if order_line.order_id.pricelist_id:
#                     list_price = order_line.product_id.currency_id._convert(
#                             list_price, order_line.order_id.pricelist_id.currency_id,
#                             self.env.user.company_id, fields.Date.today())
#                 p1 = order_line.product_id._get_product_price(order_line.order_id.pricelist_id, list_price,
#                                                               order_line.product_uom_qty, order_line.product_id.id)
#                 price = p1[order_line.product_id.id] if order_line.order_id.pricelist_id else list_price
#                 order_line.write({'price_unit': price})
        return res

#     def action_update_prices(self):
#         self.ensure_one()
#         super().action_update_prices()
#         lines_to_update = []
#         #change unit price for custom value products on click on update prices button
#         for line in self.order_line.filtered(lambda line: line.custom_val):
#             if line.product_id:
#                 # Fix for mismatch price issue of configurator and so line
#                 combination = line.product_id.product_template_attribute_value_ids
#                 # combo_price = line.product_id.product_tmpl_id._get_combination_info(combination, int(line.product_id.id or 0), int(line.product_uom_qty or 1), custom_val=line.custom_val)
#                 combo_price = line.product_id.product_tmpl_id.with_context(pricelist_id=self.pricelist_id)._get_combination_info(
#                     combination,
#                     int(line.product_id.id or 0),
#                     int(line.product_uom_qty or 1),
#                     self.pricelist_id,
#                     custom_val=line.custom_val,
#                 )
#                 print(">>>>>>>>>>>>>>>>>", combo_price)
#                 price = combo_price['price']
#                 lines_to_update.append((1, line.id, {'price_unit': price}))
# #             custom_val = line.custom_val
# #             list_price = line.product_id.price_compute('list_price', custom_val=custom_val)[line.product_id.id]
# #             if self.pricelist_id and self.pricelist_id.currency_id != line.product_id.currency_id:
# #                 list_price = line.product_id.currency_id._convert(
# #                         list_price, self.pricelist_id.currency_id, self.env.user.company_id, fields.Date.today())
# #             p1 = line.product_id._get_product_price(self.pricelist_id, list_price,
# #                                                     line.product_uom_qty, line.product_id.id)
# #             price = p1[line.product_id.id]
# #             lines_to_update.append((1, line.id, {'price_unit': price}))
#         self.update({'order_line': lines_to_update})


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    custom_val = fields.Float()
    name_description = fields.Text(related='name', readonly=False)
    is_custom_product_line = fields.Boolean()

    def _prepare_procurement_values(self):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        comming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        values = super(SaleOrderLine, self)._prepare_procurement_values()
        self.ensure_one()
        values.update({'code_intern': self._get_code_intern_description(),
                       'so_line': self})
        return values

    def get_description_following_lines(self):
        #overwrite for website description
        return self.name.splitlines()

    def _get_sale_order_line_multiline_description_sale(self):
        """Compute a default multiline description for this sales order line.
        In most cases the product description is enough but sometimes we need to append information that only
        exists on the sale order line itself.
        e.g:
        - custom attributes and attributes that don't create variants, both introduced by the "product configurator"
        - in event_sale we need to know specifically the sales order line as well as the product to generate the name:
          the product is not sufficient because we also need to know the event_id and the event_ticket_id (both which belong to the sale order line).
        """
        lang = self.order_id.partner_id.lang
        if self.env.context.get("partner_lang"):
            lang = self.env.context.get("partner_lang")
        return (
            self._get_code_intern_description() + "\n" +
            self.product_id.with_context(lang=lang).get_product_multiline_description_sale() + "" +
            self.with_context(partner_lang=lang)._get_sale_order_line_multiline_description_variants()
        )

    def _get_sale_order_line_multiline_description_sale_value(self):
        """Compute a default multiline description for this sales order line.
        In most cases the product description is enough but sometimes we need to append information that only
        exists on the sale order line itself.
        e.g:
        - custom attributes and attributes that don't create variants, both introduced by the "product configurator"
        - in event_sale we need to know specifically the sales order line as well as the product to generate the name:
          the product is not sufficient because we also need to know the event_id and the event_ticket_id (both which belong to the sale order line).
        """
        lang = self.order_id.partner_id.lang
        if self.env.context.get("partner_lang"):
            lang = self.env.context.get("partner_lang")
        return (
            self._get_code_intern_description() + "\n" +
            self.product_id.with_context(lang=lang).get_product_multiline_description_sale() + "\n" +
            self.with_context(partner_lang=lang)._get_sale_order_line_multiline_description_variants_only_value()
        )

    def _get_code_intern_description(self):
        context = self.env.context
        combination = self.product_id.product_template_attribute_value_ids
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin
        for attri in self.product_custom_attribute_value_ids:
            if (
                attri.custom_product_template_attribute_value_id.attribute_id.is_custom_attribute
            ):
                self.custom_val = attri.custom_value
        if no_variant_ptavs:
            combination += no_variant_ptavs
            ptavs = sorted(combination, key=lambda x: x.attribute_id.sequence)
            combo = []
            for attri in ptavs:
                combo.append(attri.id)
            combination = self.env["product.template.attribute.value"].browse(combo)
        refcode = self.product_id.get_internal_ref(
            self.custom_val, combination=combination
        )
        if context and context.get("only_code", False):
            return refcode
        refcode = "Code intern:" + refcode
        return refcode

    def _get_sale_order_line_multiline_description_variants_only_value(self):
        """When using no_variant attributes or is_custom values, the product
        itself is not sufficient to create the description: we need to add
        information about those special attributes and values.

        only display attribute value
        :return: the description related to special variant attributes/values
        :rtype: string
        """

        name = ""

        lang = self.env.context.get('partner_lang') or self.order_id.partner_id.lang

        custom_ptavs = self.product_custom_attribute_value_ids.custom_product_template_attribute_value_id
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin

        combination = self.product_id.product_template_attribute_value_ids
        if no_variant_ptavs:
            combination += no_variant_ptavs
            ptavs = sorted(combination, key=lambda x: x.attribute_id.sequence)
            combo = []
            for attri in ptavs:
                combo.append(attri.id)
            combination = self.env['product.template.attribute.value'].browse(combo)

        # Collecting the attribute values in a list for display
        attributes = []
        for ptav in combination:
            if ptav.id not in custom_ptavs.ids:
                attributes.append(ptav.with_context(lang=lang).product_attribute_value_id.name)

        # Sorting the custom attribute values based on _order settings
        custom_values = sorted(self.product_custom_attribute_value_ids,
                               key=lambda r: (r.custom_product_template_attribute_value_id.id, r.id))

        for pacv in custom_values:
            name += "\n" + "%s: %s" % (pacv.custom_product_template_attribute_value_id.name, pacv.custom_value)
            attributes.append(name)

        if attributes:
            name = f"({','.join(attributes)})"
        return name

    def _get_sale_order_line_multiline_description_variants(self):
        """When using no_variant attributes or is_custom values, the product
        itself is not sufficient to create the description: we need to add
        information about those special attributes and values.
        :return: the description related to special variant attributes/values
        :rtype: string
        """

        name = ""

        lang = self.env.context.get('partner_lang') or self.order_id.partner_id.lang

        custom_ptavs = self.product_custom_attribute_value_ids.custom_product_template_attribute_value_id
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin

        combination = self.product_id.product_template_attribute_value_ids
        if no_variant_ptavs:
            combination += no_variant_ptavs
            ptavs = sorted(combination, key=lambda x: x.attribute_id.sequence)
            combo = []
            for attri in ptavs:
                combo.append(attri.id)
            combination = self.env['product.template.attribute.value'].browse(combo)

        
        for ptav in combination:
            if ptav.id not in custom_ptavs.ids:
                name += "\n" + ptav.with_context(lang=lang).display_name

        # Sort the values according to _order settings, because it doesn't work for virtual records in onchange
        custom_values = sorted(self.product_custom_attribute_value_ids, key=lambda r: (r.custom_product_template_attribute_value_id.id, r.id))
        # display the is_custom values
        for pacv in custom_values:
            name += "\n" + pacv.with_context(lang=lang).display_name

        return name

    @api.model_create_multi
    def create(self, vals_list):
        Product = self.env['product.product']

        for vals in vals_list:
            # vals['is_custom_product_line'] = False
            # Step 1: get custom_val
            custom_val = False
            pcav_ids = vals.get("product_custom_attribute_value_ids")

            if pcav_ids:
                for cmd in pcav_ids:
                    if isinstance(cmd, (list, tuple)) and len(cmd) > 2 and cmd[2]:
                        custom_val = cmd[2].get("custom_value")
                        if custom_val:
                            vals["custom_val"] = custom_val
                            break

            # Step 2: only continue if custom_val exists
            if custom_val and vals.get("name"):
                name = vals.get("name")

                # Step 3: extract "Code intern"
                match = re.search(r"Code intern:\s*([A-Z0-9.]+)", name)
                if match:
                    internal_code = match.group(1)

                    # Step 4: search product with default_code
                    product = Product.search(
                        ['|', ('default_code', '=', internal_code),
                         ('product_internal_reference_ids.name', '=', internal_code.strip()), ],
                        limit=1
                    )

                    if product:
                        # Step 5: override product fields
                        vals.update({
                            "product_id": product.id,
                            "product_template_id": product.product_tmpl_id.id,
                            "is_custom_product_line": True
                        })

        records = super().create(vals_list)

        # NOW YOU CAN CALL METHODS ON REAL RECORDS
        for line in records.filtered(lambda sol: sol.is_custom_product_line):
            line.write({
                'name': (
                        (line._get_code_intern_description() or "") + "\n" +
                        (line.product_id.get_product_multiline_description_sale() or "") + "\n" +
                        (line._get_sale_order_line_multiline_description_variants() or "")
                ),
                'name_description': (
                        (line._get_code_intern_description() or "") + "\n" +
                        (line.product_id.get_product_multiline_description_sale() or "") + "\n" +
                        (line._get_sale_order_line_multiline_description_variants() or "")
                )
            })

        return records

    def _get_display_price(self):
        context = dict(
            self.env.context,
            pricelist=self.order_id.pricelist_id if self.order_id.pricelist_id else False,
            fiscalposition=self.order_id.fiscal_position_id
        )

        for attri in self.product_custom_attribute_value_ids:
            if (
                    attri.custom_product_template_attribute_value_id.attribute_id.is_custom_attribute
            ):
                self.custom_val = attri.custom_value
        # Fix for mismatch price issue of configurator and so line
        if self.product_id:
            combination = self.product_id.product_template_attribute_value_ids
            combo_price = self.product_id.product_tmpl_id._get_combination_info(
                combination,
                int(self.product_id.id or 0),
                int(self.product_uom_qty or 1),
                custom_val=self.custom_val,
                context=context,
            )
            return combo_price["price"]
        else:
            return super()._get_display_price()


from odoo import http, SUPERUSER_ID, _
from odoo.http import request, Controller, route
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.cart import Cart
from odoo.addons.website_sale.controllers.payment import PaymentPortal
from odoo.addons.sale.controllers.product_configurator import (
    SaleProductConfiguratorController,
)
from odoo.addons.website.controllers.main import Website
from datetime import datetime
from odoo.tools.translate import LazyTranslate, _
from odoo.exceptions import ValidationError
import logging

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)


class WebsiteSaleCartController(Cart):
    """
        Extend website cart behavior for:
        1) add to cart -> update/create cutting charge line
        2) remove from cart -> delete related cutting info + update/remove cutting charge line
        """

    def _sync_cutting_charge_line(self, order_sudo):
        """
        Recalculate cutting charge qty from all remaining cutting_info_ids.
        If qty > 0 -> create/update service line
        If qty == 0 -> remove service line
        """
        if not order_sudo:
            return

        cutting_product = request.env.ref(
            'website_nexconect.product_product_cable_cutting_charges',
            raise_if_not_found=False
        ).sudo()
        if not cutting_product:
            return

        # Total cutting service qty = total pieces across all cutting info lines
        charge_qty = int(sum(order_sudo.cutting_info_ids.mapped('no_of_piece')))

        charge_line = order_sudo.order_line.filtered(
            lambda l: l.product_id.id == cutting_product.id
        )[:1]

        if charge_qty > 0:
            price_unit = order_sudo.pricelist_id._get_product_price(cutting_product, 1.0) or 0.0

            if charge_line:
                charge_line.sudo().write({
                    'product_uom_qty': charge_qty,
                    'price_unit': price_unit,
                })
            else:
                request.env['sale.order.line'].sudo().create({
                    'order_id': order_sudo.id,
                    'product_id': cutting_product.id,
                    'name': cutting_product.get_product_multiline_description_sale() or cutting_product.name,
                    'product_uom_qty': charge_qty,
                    'price_unit': price_unit,
                })
        else:
            if charge_line:
                charge_line.sudo().unlink()

    @route(
        route='/shop/cart/add',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
        sitemap=False
    )
    def add_to_cart(
            self,
            product_template_id,
            product_id,
            quantity=1.0,
            uom_id=None,
            product_custom_attribute_values=None,
            no_variant_attribute_value_ids=None,
            linked_products=None,
            **kwargs
    ):
        res = super(WebsiteSaleCartController, self).add_to_cart(
            product_template_id=product_template_id,
            product_id=product_id,
            quantity=quantity,
            uom_id=uom_id,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_value_ids=no_variant_attribute_value_ids,
            linked_products=linked_products,
            **kwargs
        )

        order_sudo = request.cart or request.website._create_cart()
        self._sync_cutting_charge_line(order_sudo)

        return res

    @route()
    def update_cart(self, line_id, quantity, product_id=None, **kwargs):
        """
        Called by base cart page when:
        - quantity is changed
        - remove button is clicked (quantity becomes 0)

        If a product line is removed:
        - remove all cutting_info_ids for that same product
        - then recalculate/remove cutting charge line
        """
        order_sudo_before = request.cart or request.website.sale_get_order()
        removed_product_id = None

        # detect which product is about to be removed BEFORE super()
        if order_sudo_before and line_id:
            try:
                line_id = int(line_id)
            except Exception:
                line_id = False

            try:
                quantity_int = int(quantity)
            except Exception:
                quantity_int = 0

            if line_id and quantity_int <= 0:
                line = order_sudo_before.order_line.filtered(lambda l: l.id == line_id)[:1]
                if line:
                    cutting_product = request.env.ref(
                        'website_nexconect.product_product_cable_cutting_charges',
                        raise_if_not_found=False
                    )
                    # Ignore if user is removing the service product itself
                    if not cutting_product or line.product_id.id != cutting_product.id:
                        removed_product_id = line.product_id.id

        # standard Odoo cart update
        values = super(WebsiteSaleCartController, self).update_cart(
            line_id, quantity, product_id=product_id, **kwargs
        )

        order_sudo_after = request.cart or request.website.sale_get_order()

        # remove related cutting info lines only for removed product
        if order_sudo_after and removed_product_id:
            related_cutting_lines = order_sudo_after.cutting_info_ids.filtered(
                lambda l: l.product_id.id == removed_product_id
            )
            if related_cutting_lines:
                related_cutting_lines.unlink()

        # always sync charge line after cart update
        self._sync_cutting_charge_line(order_sudo_after)

        return values


class WebsiteSaleCuttingController(http.Controller):

    @http.route(
        '/cable/cutting/save',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
        sitemap=False
    )
    def save_cutting_lines(self, product_id, quantity, cutting_lines=None, **kwargs):
        """
        Save cutting lines as NEW batch every time.
        Do not remove previous same-product lines.
        """

        # 1) get current cart if already exists
        order_sudo = request.cart

        # 2) if no cart exists, create it now
        if not order_sudo:
            order_sudo = request.website._create_cart()

        if not order_sudo:
            return {
                'success': False,
                'error': 'Could not create cart.',
            }

        product_id = int(product_id or 0)
        qty = float(quantity or 0)

        if not product_id:
            return {
                'success': False,
                'error': 'Product not found.',
            }

        # 3) build one2many values
        vals_list = []
        total = 0.0

        for line in cutting_lines or []:
            pieces = int(float(line.get('pieces', 0) or 0))
            meters = float(line.get('length', 0) or 0)

            if pieces <= 0 or meters <= 0:
                continue

            line_total = pieces * meters
            total += line_total

            vals_list.append((0, 0, {
                'product_id': product_id,
                'sale_order_id': order_sudo.id,
                'no_of_piece': pieces,
                'no_of_meter': meters,
            }))

        # 4) backend validation
        if round(total, 2) != round(qty, 2):
            return {
                'success': False,
                'error': f'Total cutting length must be equal to ordered quantity ({qty}).',
            }

        # 5) APPEND new lines only
        # IMPORTANT: do not unlink old lines, because user may add same product again later
        if vals_list:
            order_sudo.write({
                'cutting_info_ids': vals_list
            })

        return {
            'success': True,
            'order_id': order_sudo.id,
            'cart_quantity': order_sudo.cart_quantity,
        }


class WebsiteInherit(Website):

    @http.route('/website/snippet/autocomplete', type='jsonrpc', auth='public', website=True, readonly=True)
    def autocomplete(self, search_type=None, term=None, order=None, limit=5, max_nb_chars=999, options=None):
        result = super().autocomplete(search_type=search_type, term=term, order=order, limit=limit, max_nb_chars=max_nb_chars, options=options)
        if not result or not result.get('results'):
            return result

        for rec in result['results']:
            if 'detail_strike' in rec:
                rec['detail_strike'] = False

            if request.env.user._is_public():
                if 'detail' in rec:
                    rec['detail'] = False
        return result


class ProductConfiguratorControllerCustom(SaleProductConfiguratorController):

    @route(route="/sale_product_configurator/update_combination", type="jsonrpc", auth="user", methods=['POST'],
           readonly=True, website=True)
    def sale_product_configurator_update_combination(
            self,
            product_template_id,
            ptav_ids,
            currency_id,
            so_date,
            quantity,
            product_uom_id=None,
            company_id=None,
            pricelist_id=None,
            customValue=None,
            **kwargs,
    ):
        res = super(ProductConfiguratorControllerCustom, self).sale_product_configurator_update_combination(
            product_template_id,
            ptav_ids,
            currency_id,
            so_date,
            quantity,
            product_uom_id=product_uom_id,
            company_id=company_id,
            pricelist_id=pricelist_id,
            customValue=customValue,
            **kwargs,
        )

        res.pop("can_be_sold", None)
        res.pop("strikethrough_price", None)

        if customValue and customValue != 0:
            product_template = request.env["product.template"].browse(product_template_id)
            combination = request.env['product.template.attribute.value'].browse(ptav_ids)
            product = product_template._get_variant_for_combination(combination)

            combination_info = product_template._get_combination_info(
                combination=combination,
                product_id=product and int(product),
                add_qty=quantity and float(quantity) or 1.0,
                custom_val=customValue,
                custom_pricelist=pricelist_id or False,
            )
            if combination_info and combination_info.get("price") and customValue:
                res.update({"price": combination_info.get("price")})
        return res


class WebsiteSaleVariantController(Controller):

    @route(
        '/website_sale/get_combination_info',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
        readonly=True,
    )
    def get_combination_info_website(
            self, product_template_id, product_id, combination, add_qty, uom_id=None, custom_val=None,
            **kwargs
    ):
        product_template_id = product_template_id and int(product_template_id)
        product_id = product_id and int(product_id)
        add_qty = (add_qty and float(add_qty)) or 1.0

        product_template = request.env['product.template'].sudo().browse(product_template_id)

        combination_info = product_template._get_combination_info(
            combination=request.env['product.template.attribute.value'].sudo().browse(
                combination),
            product_id=product_id,
            add_qty=add_qty,
            uom_id=uom_id,
            custom_val=custom_val,
        )
        product = request.env['product.product'].sudo().browse(combination_info['product_id'])

        # Pop data only computed to ease server-side computations.
        for key in (
                # Only provided to ease server-side computations.
                'product_taxes', 'taxes', 'currency', 'date', 'combination',
                # Only used in Google Merchant Center logic, not client-side.
                'discount_start_date', 'discount_end_date'
        ):
            combination_info.pop(key)

        # if product and product.id == product_id:
        #     combination_info['no_product_change'] = True
        #     return combination_info

        if request.website.product_page_image_width != 'none' and not request.env.context.get('website_sale_no_images',
                                                                                              False):
            product_or_template = product or product_template
            combination_info['display_image'] = bool(product_or_template.image_128)
            combination_info['carousel'] = request.env['ir.ui.view']._render_template(
                'website_sale.shop_product_images',
                values={
                    'product': product_template,
                    'product_variant': product,
                    'website': request.website,
                },
            )

        if request.website.is_view_active('website_sale.product_tags'):
            all_tags = product.all_product_tag_ids if product else product_template.product_tag_ids
            combination_info['product_tags'] = request.env['ir.ui.view']._render_template(
                'website_sale.product_tags', values={
                    'all_product_tags': all_tags.filtered('visible_to_customers'),
                }
            )

        # Get the warehouse we're working on as well as its locations.
        if request.env.context.get('warehouse'):
            warehouse = request.env['stock.warehouse'].sudo().browse(
                request.env.context['warehouse'])
        else:
            warehouse = request.env['stock.warehouse'].sudo().search([
                ('company_id', '=', request.env.company.id)
            ], limit=1)
            request.update_context = dict(request.env.context, warehouse=warehouse.id)
        wh_location_ids = [loc['id'] for loc in request.env['stock.location'].sudo().search_read(
            [('id', 'child_of', warehouse.view_location_id.id)],
            ['id'],
        )]
        wh_stock_location = warehouse.lot_stock_id
        product_template_ids = product_template.ids
        product_variant_ids = []
        if product_id:
            product_variant_ids = product_id
        ForecastedReport = request.env['stock.forecasted_product_template']
        lines = ForecastedReport.sudo()._get_report_lines(
            product_template_ids, product_variant_ids, wh_location_ids, wh_stock_location)
        # combination_info['forcasted_date_list'] = []
        # forcasted_date_list = False

        combination_info['forecasted_data'] = []
        forcasted_date_list = []

        for line in lines:
            document_in = line.get('document_in')
            document_out = line.get('document_out')
            uom_in = line.get('uom_id')
            if document_in and not document_out and document_in.get('_name') == 'purchase.order' and document_in.get(
                    'id') and line.get('product').get('id') == combination_info['product_id']:
                document_in_date = document_in.get('id')
                uom_name = uom_in.get('name')
                qty_line = line.get('quantity')
                order = request.env['purchase.order'].sudo().browse(document_in_date)
                forcasted_date_list.append(datetime.strftime(order.date_planned, '%d %B %Y'))

                forecasted_date = 'TBC'
                if order.x_studio_expected_arrival:
                    forecasted_date = datetime.strftime(order.x_studio_expected_arrival, '%d %B %Y')

                forecasted_data = {
                    'forecasted_date': forecasted_date,
                    'qty': qty_line,
                    'uom': uom_name
                }
                combination_info['forecasted_data'].append(forecasted_data)

        # for line in lines:
        #     if line.get('document_in', False) and \
        #        line.get('document_in', False)._name == 'purchase.order':
        #         document_in = line.get('document_in', False)
        #         #forcasted_date_list = line.get('receipt_date')
        #         if document_in.date_planned:
        #             forcasted_date_list = document_in.date_planned

        combination_info['forecasted_data'] = sorted(
            combination_info['forecasted_data'],
            key=lambda x: datetime.strptime(x['forecasted_date'], '%d %B %Y') if x[
                                                                                     'forecasted_date'] != 'TBC' else datetime.max,
            reverse=True
        )
        combination_info['quantity_transit'] = bool(combination_info['forecasted_data'])

        # Recursive BOM + Stock Availability Calculation
        def compute_total_available_qty(product):
            """Compute total available quantity = on-hand stock + recursive BOM-based production."""
            quant_obj = request.env['stock.quant'].sudo()

            # 1. Stock in internal locations
            stock = quant_obj.search([
                ('location_id.usage', '=', 'internal'),
                ('product_id', '=', product.id)
            ])
            stock_qty = sum(stock.mapped('available_quantity'))

            # 2. Recursively check BOM production availability
            extra_manufacture_qty = 0
            if product.bom_ids:
                bom = product.bom_ids.filtered(lambda b: b.type == 'normal')
                if bom:
                    bom = bom[0]
                    component_quantities = []

                    for line in bom.bom_line_ids:
                        required_per_unit = line.product_qty
                        component = line.product_id

                        # Recursive call
                        available_component_qty = compute_total_available_qty(component)

                        if required_per_unit > 0:
                            can_make = available_component_qty // required_per_unit
                            component_quantities.append(can_make)

                    if component_quantities:
                        extra_manufacture_qty = int(min(component_quantities))

            # 3. Total = stock + BOM-based production
            return stock_qty + extra_manufacture_qty

        # Final mo_qty for main product
        mo_qty = 0
        if product.bom_ids:
            main_bom = product.bom_ids.filtered(lambda b: b.type == 'normal')
            if main_bom:
                main_bom = main_bom[0]
                final_qty_list = []

                for bom_line in main_bom.explode(product, 1)[1]:
                    line = bom_line[0]
                    required_qty = line.product_qty
                    component = line.product_id

                    total_available = compute_total_available_qty(component)

                    if required_qty > 0:
                        can_make = total_available // required_qty
                        final_qty_list.append(can_make)

                if final_qty_list:
                    mo_qty = int(min(final_qty_list))

        combination_info['mo_qty'] = mo_qty
        combination_info['display_mo_qty'] = bool(product.bom_ids)

        return combination_info


class WebsiteSaleExtend(WebsiteSale):

    @http.route('/shop/remove/session', type='http', auth='public', website=True, sitemap=False)
    def remove_item_on_cart(self, **kw):
        # Get the current sale order from the session
        sale_order = request.cart
        _logger.info(
            "Sale Order : %s",
            request.cart
        )
        request.session['sale_order_id'] = None
        request.session['website_sale_cart_quantity'] = None

        if sale_order:
            sale_order.sudo().write({'save_from_cart': True})

        values = {
            'order': sale_order,
        }
        return request.render("website_nexconect.confirmation_sale", values)

    @http.route(['/shop/cart/add_from_portal'], type='http', auth='public', itemap=False,
                website=True)
    def add_from_portal_to_cart(self, order_id, **kwargs):
        # Get the sale order based on the order_id
        order_id = int(order_id)
        SaleOrder = request.env['sale.order']
        order = SaleOrder.sudo().browse((order_id))
        request.session['sale_order_id'] = order_id
        request.session['website_sale_cart_quantity'] = order.cart_quantity

        order.update_display_message_from_portal = True

        return request.redirect('/shop/cart')

    @http.route(['/shop/cart'], type='http', auth="user",
                website=True, sitemap=False)
    def cart(self, access_token=None, revive='', **post):
        request.website = request.website.with_context({'sale_order_id': request.session.get('sale_order_id')})
        response = super(WebsiteSaleExtend, self).cart(
            access_token=access_token, revive=revive, **post)
        return response

    @http.route('/shop/payment/validate', type='http', auth="public", website=True, sitemap=False)
    def shop_payment_validate(self, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        if sale_order_id is None:
            order_sudo = request.cart
            if not order_sudo and 'sale_last_order_id' in request.session:
                # Retrieve the last known order from the session if the session key `sale_order_id`
                # was prematurely cleared. This is done to prevent the user from updating their cart
                # after payment in case they don't return from payment through this route.
                last_order_id = request.session['sale_last_order_id']
                order_sudo = request.env['sale.order'].sudo().browse(
                    last_order_id).exists()
        else:
            order_sudo = request.env['sale.order'].sudo().browse(sale_order_id)
            assert order_sudo.id == request.session.get('sale_last_order_id')

        if not order_sudo:
            return request.redirect(self._get_shop_path())

        errors = self._get_shop_payment_errors(order_sudo) if order_sudo.state != 'sale' else []

        if errors:
            first_error = errors[0]  # only display first error
            error_msg = f"{first_error[0]}\n{first_error[1]}"
            raise ValidationError(error_msg)

        tx_sudo = order_sudo.get_portal_last_transaction()
        if order_sudo.amount_total and not tx_sudo:
            return request.redirect(self._get_shop_path())

        old_shipping_partner = order_sudo.partner_shipping_id
        old_billing_partner = order_sudo.partner_invoice_id
        if order_sudo.partner_id.parent_id:
            order_sudo.partner_id = order_sudo.partner_id.parent_id
            # When we change the partner using above code,
            # It will also change the shipping address and invoice address of the sale order bcs of the standard code.
            # So we loose the selected partner when creating the order from website.
            # Here we again update the selected partner to the sale order.
            order_sudo.partner_shipping_id = old_shipping_partner
            order_sudo.partner_invoice_id = old_billing_partner

        if order_sudo.x_studio_delivery_contact_1.parent_id:
            order_sudo.x_studio_delivery_contact_1 = order_sudo.x_studio_delivery_contact_1.parent_id

        if not order_sudo.amount_total and not tx_sudo and order_sudo.state != 'sale':
            order_sudo._check_cart_is_ready_to_be_paid()
            # Only confirm the order if it wasn't already confirmed.
            order_sudo._validate_order()

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        if tx_sudo and tx_sudo.state == 'draft':
            return request.redirect(self._get_shop_path())

        return request.redirect('/shop/confirmation')

    @http.route(['/shop/checkout'], type='http', methods=['GET'], auth="user",
                website=True, sitemap=False, list_as_website_content=_lt("Shop Checkout"))
    def shop_checkout(self, try_skip_step=None, **query_params):
        response = super(WebsiteSaleExtend, self).shop_checkout(try_skip_step, **query_params)
        return response

    def _get_shop_payment_values(self, order, **kwargs):
        values = super(WebsiteSaleExtend, self)._get_shop_payment_values(order, **kwargs)
        values.update({
            'submit_button_label': _("Confirm Order"),
        })
        return values

    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=WebsiteSale.sitemap_shop)
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        response = super(WebsiteSaleExtend, self).shop(page=page, category=category, search=search, min_price=min_price,
                                                       max_price=max_price, ppg=ppg, **post)
        if request.env.user._is_public() and response.qcontext.get('categories'):
            categories = response.qcontext.get('categories').filtered(
                lambda c: not c.activate_subcategory_filter_using_customer)
            if categories:
                response.qcontext['categories'] = categories
        return response


class PaymentPortalExtend(PaymentPortal):

    @http.route(
        '/shop/payment/transaction/<int:order_id>', type='jsonrpc', auth='public', website=True
    )
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        """while confirm the order from website then remove the open in shop button from portal view."""
        response = super(PaymentPortalExtend, self).shop_payment_transaction(order_id, access_token, **kwargs)
        request.env['sale.order'].browse(order_id).sudo().write({'save_from_cart': False})
        return response

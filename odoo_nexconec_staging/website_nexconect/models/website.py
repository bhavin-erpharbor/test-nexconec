# -*- coding: utf-8 -*-

from odoo import models,  _
from odoo.exceptions import MissingError
from odoo.http import request

CART_SESSION_CACHE_KEY = 'sale_order_id'


class Website(models.Model):
    _inherit = 'website'

    # def _prepare_sale_order_values(self, partner_sudo):
    #     res = super(Website, self)._prepare_sale_order_values(partner_sudo)
    #     # if res and partner_sudo and partner_sudo.id.parent_id:
    #     #     res['partner_invoice_id'] = partner_sudo.id.parent_id.id
    #     return res

    # def _get_and_cache_current_cart(self):
    #     if self.env.context.get('sale_order_id'):
    #         request.session['sale_order_id'] = (self.env.context.get('sale_order_id'))
    #     sale_order = super(Website, self)._get_and_cache_current_cart()
    #     partner = self.env.user.partner_id
    #     sale_order_id = request.session.get('sale_order_id')
    #     if partner and sale_order and partner.parent_id:
    #         if sale_order.partner_id.id != partner.id and request.website.partner_id.id != partner.id:
    #             sale_order.write({'partner_invoice_id': partner.parent_id.id})
    #             sale_order._onchange_partner_shipping_id()
    #     return sale_order

    def _get_and_cache_current_cart(self):
        """ Retrieves and caches the current cart for the session.
            Overwrite the method due to when confirm order from website then
            display the abandonned so quantity.
        """
        self.ensure_one()

        SaleOrderSudo = self.env['sale.order'].sudo()

        sale_order_sudo = SaleOrderSudo
        if CART_SESSION_CACHE_KEY in request.session:
            sale_order_sudo = SaleOrderSudo.browse(request.session[CART_SESSION_CACHE_KEY])

            try:
                # fetch the record field or raise a missingError
                # avoids a query with the use of exists()
                sale_order_sudo and sale_order_sudo.state
            except MissingError:
                self.sale_reset()
                sale_order_sudo = SaleOrderSudo

            if sale_order_sudo and (
                sale_order_sudo.state != 'draft'
                or sale_order_sudo.get_portal_last_transaction().state in (
                    'pending', 'authorized', 'done'
                )
                or sale_order_sudo.website_id != self
            ):
                self.sale_reset()
                sale_order_sudo = SaleOrderSudo

            # If customer logs in, the cart must be recomputed based on his information (in the
            # first non readonly request).
            if (
                sale_order_sudo
                and not self.env.user._is_public()
                and self.env.user.partner_id.id != sale_order_sudo.partner_id.id
                and not request.env.cr.readonly
            ):
                sale_order_sudo._update_address(self.env.user.partner_id.id, ['partner_id'])
        elif (
            self.env.user
            and not self.env.user._is_public()
            # If the company of the partner doesn't allow them to buy from this website, updating
            # the cart customer would raise because of multi-company checks.
            # No abandoned cart should be returned in this situation.
            and self.env.user.partner_id.filtered_domain(
                self.env['res.partner']._check_company_domain(self.company_id.id)
            )
        ):  # Search for abandonned cart.
            partner_sudo = self.env.user.partner_id
            abandonned_cart_sudo = SaleOrderSudo.search([
                ('partner_id', '=', partner_sudo.id),
                ('website_id', '=', self.id),
                ('state', '=', 'draft'),
                # customization start
                ('save_from_cart', '=', False)
                # customization end
            ], limit=1)
            if abandonned_cart_sudo:
                if not request.env.cr.readonly:
                    # Force the recomputation of the pricelist and fiscal position when resurrecting
                    # an abandonned cart
                    abandonned_cart_sudo._update_address(partner_sudo.id, ['partner_id'])
                    abandonned_cart_sudo._verify_cart()
                sale_order_sudo = abandonned_cart_sudo


        if (
            (sale_order_sudo or not self.env.user._is_public())
            and sale_order_sudo.id != request.session.get(CART_SESSION_CACHE_KEY)
        ):
            # Store the id of the cart if there is one, or False if the user is logged in, to avoid
            # searching for an abandoned cart again for that user.
            request.session[CART_SESSION_CACHE_KEY] = sale_order_sudo.id
            if 'website_sale_cart_quantity' not in request.session:
                request.session['website_sale_cart_quantity'] = sale_order_sudo.cart_quantity
        return sale_order_sudo

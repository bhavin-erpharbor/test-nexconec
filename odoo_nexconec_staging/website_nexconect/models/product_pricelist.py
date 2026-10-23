# -*- coding: utf-8 -*-
from itertools import chain
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"


    def _compute_base_price(self, product, quantity, uom, date, currency, **kwargs):
        """ Compute the base price for a given rule

        :param product: recordset of product (product.product/product.template)
        :param float qty: quantity of products requested (in given uom)
        :param uom: unit of measure (uom.uom record)
        :param datetime date: date to use for price computation and currency conversions
        :param currency: currency in which the returned price must be expressed

        :returns: base price, expressed in provided pricelist currency
        :rtype: float
        """
        currency.ensure_one()
        rule_base = self.base or 'list_price'
        if rule_base == 'pricelist' and self.base_pricelist_id:
            price = self.base_pricelist_id._get_product_price(
                product, quantity, currency=self.base_pricelist_id.currency_id, uom=uom, date=date,
                **kwargs
            )
            src_currency = self.base_pricelist_id.currency_id
        elif rule_base == "standard_price":
            src_currency = product.cost_currency_id
            price = product.with_context(custom_price=self.env.context.get('custom_price'),pid=self.env.context.get('pid'))._price_compute('list_price', rule_base, date=date)[product.id]
        else: # list_price
            src_currency = product.currency_id
            price = product.with_context(custom_price=self.env.context.get('custom_price'),pid=self.env.context.get('pid'))._price_compute('list_price',custom_val=self.env.context.get('custom_val'))[product.id]
        if src_currency != currency:
            price = src_currency._convert(price, currency, self.env.company, date, round=False)

        return price
    
class Pricelist(models.Model):
    _inherit = "product.pricelist"

    customer_pricelist_ids = fields.One2many(
        'res.partner',
        'specific_property_product_pricelist',
        string="Customer Pricelist"
    )
    company_customer_pricelist_ids = fields.One2many(
        'res.partner',
        compute='_compute_company_customers',
        string='Customers'
    )

    def _compute_company_customers(self):
        for rec in self:
            rec.company_customer_pricelist_ids = rec.customer_pricelist_ids.filtered(
                lambda p: not p.parent_id
            )

    def _compute_price_rule(
            self, products, quantity, currency=None, uom=None, date=False, compute_price=True,
            **kwargs
    ):
        """ Low-level method - Mono pricelist, multi products
        Returns: dict{product_id: (price, suitable_rule) for the given pricelist}

        Note: self and self.ensure_one()

        :param products: recordset of products (product.product/product.template)
        :param float quantity: quantity of products requested (in given uom)
        :param currency: record of currency (res.currency)
                         note: currency.ensure_one()
        :param uom: unit of measure (uom.uom record)
            If not specified, prices returned are expressed in product uoms
        :param date: date to use for price computation and currency conversions
        :type date: date or datetime
        :param bool compute_price: whether the price should be computed (default: True)

        :returns: product_id: (price, pricelist_rule)
        :rtype: dict
        """
        self and self.ensure_one()  # self is at most one record

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.ensure_one()

        if not products:
            return {}

        if not date:
            # Used to fetch pricelist rules and currency rates
            date = fields.Datetime.now()

        # Fetch all rules potentially matching specified products/templates/categories and date
        rules = self._get_applicable_rules(products, date, **kwargs)

        results = {}
        for product in products:
            suitable_rule = self.env['product.pricelist.item']

            product_uom = product.uom_id
            target_uom = product_uom  # If no uom is specified, fall back on the product uom

            # Compute quantity in product uom because pricelist rules are specified
            # w.r.t product default UoM (min_quantity, price_surchage, ...)
            if target_uom != product_uom:
                qty_in_product_uom = target_uom._compute_quantity(
                    quantity, product_uom, raise_if_failure=False
                )
            else:
                qty_in_product_uom = quantity

            for rule in rules:
                if rule._is_applicable_for(product, qty_in_product_uom):
                    suitable_rule = rule
                    break

            if compute_price:
                price = suitable_rule._compute_price(
                    product, quantity, target_uom, date=date, currency=currency)
            else:
                # Skip price computation when only the rule is requested.
                price = 0.0
            results[product.id] = (price, suitable_rule.id)

        return results
    
    
    # def _get_products_price(self, products, *args, **kwargs):
    #     """Compute the pricelist prices for the specified products, quantity & uom.

    #     Note: self and self.ensure_one()

    #     :param products: recordset of products (product.product/product.template)
    #     :param float quantity: quantity of products requested (in given uom)
    #     :param currency: record of currency (res.currency) (optional)
    #     :param uom: unit of measure (uom.uom record) (optional)
    #         If not specified, prices returned are expressed in product uoms
    #     :param date: date to use for price computation and currency conversions (optional)
    #     :type date: date or datetime

    #     :returns: {product_id: product price}, considering the current pricelist if any
    #     :rtype: dict(int, float)
    #     """
    #     custom_price = self.env.context.get('custom_price')
    #     pid = self.env.context.get('pid')
    #     self and self.ensure_one()  # self is at most one record
    #     return {
    #         product_id: res_tuple[0]
    #         for product_id, res_tuple in self.with_context(custom_price=custom_price,pid=pid)._compute_price_rule(products,compute_price=custom_price , *args, **kwargs).items()
    #     }
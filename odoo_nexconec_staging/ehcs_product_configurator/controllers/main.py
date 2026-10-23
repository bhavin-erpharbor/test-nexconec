# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.sale.controllers.product_configurator import SaleProductConfiguratorController
from datetime import datetime
from odoo.http import Controller, request, route
from odoo.tools.safe_eval import safe_eval
import logging

_logger = logging.getLogger(__name__)


class ProductConfiguratorControllerInherit(SaleProductConfiguratorController):

    @route('/configurator/internal_ref', type='jsonrpc', auth='user')
    def get_internal_ref(self, product_id, custom_val=False, combination=False):
        generated_code = ""
        product = request.env['product.product'].browse(product_id)
        if not combination:
            combination = product.product_template_attribute_value_ids
        calculator_price = len(combination.filtered(lambda l: l.attribute_id.custom_cal == True))
        if product.default_code:
            generated_code += " " + product.default_code
        elif product.product_tmpl_id.default_code:
            generated_code += " " + product.product_tmpl_id.default_code
        else:
            pass
        if calculator_price > 0:
            # generated_code += "("
            for attri in combination:
                if attri.attribute_id.is_custom_attribute:
                    val = float(custom_val) if custom_val else attri.custom_value
                    generated_code += '{0:g}'.format(val)# + ","
                elif attri.ref_code:
                    generated_code += attri.ref_code#  + ","
                else:
                    pass
            # generated_code += ")"
        return generated_code

    @route(route='/sale_product_configurator/get_multi_products', type='jsonrpc', auth='user', readonly=True)
    def sale_product_configurator_get_multi_products(
        self,
        product_template_id,
        combination,
        currency_id,
        so_date,
        quantity,
        product_uom_id=None,
        company_id=None,
        pricelist_id=None,
        parent_combination=None,
        customValue=''
    ):
        if company_id:
            request.update_context(allowed_company_ids=[company_id])
        product_template = request.env['product.template'].browse(product_template_id)
        combination = request.env['product.template.attribute.value'].browse(combination)
        pricelist_id = request.env['product.pricelist'].browse(pricelist_id)
        currency_id = request.env['res.currency'].browse(currency_id)
        return [
                dict(
                    **self._get_product_information(
                        product_template,
                        combination,
                        currency_id,
                        pricelist_id,
                        datetime.fromisoformat(so_date),
                        quantity=quantity,
                        product_uom_id=product_uom_id,
                        parent_combination=parent_combination,
                        show_packaging=True,
                    ),
                    parent_product_tmpl_ids=[product_template.id],
                    customValue=customValue
                )
            ],
 
# -*- coding: utf-8 -*-
import odoo
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.http import request
from odoo import api, fields, models, _
from math import fabs
from odoo.exceptions import UserError

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _get_product_description(self, product_id):
        lang = self.env.context.get('partner_lang') or self.env.user.lang
        product = product_id
        description = product.with_context(lang=lang).get_product_multiline_description_sale()
        return description

    def _get_product_variant_description(self, product_id, combination):
        lang = self.env.context.get('partner_lang') or self.env.user.lang
        name = ""
        for ptav in combination:
            name += "\n" + ptav.with_context(lang=lang).display_name
        return name

    def _get_sale_order_line_multiline_description_variants(self, product_id, combination):
        lang = self.env.context.get('partner_lang') or self.env.user.lang
        name = ""
        custom_ptavs = product_id.product_custom_attribute_value_ids.custom_product_template_attribute_value_id
        no_variant_ptavs = product_id.product_no_variant_attribute_value_ids._origin
        combination = product_id.product_template_attribute_value_ids
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

        custom_values = sorted(product_id.product_custom_attribute_value_ids, key=lambda r: (r.custom_product_template_attribute_value_id.id, r.id))
        for pacv in custom_values:
            name += "\n" + pacv.with_context(lang=lang).display_name

        return name

    def _get_product_multiline_description(self, product_id, combination):
        description = self._get_product_description(product_id)
        variant_description = self._get_product_variant_description(product_id, combination)
        return description + variant_description

class ReportMrpProduction(models.Model):
    _inherit = "report.mrp.production"

    def _get_report_values(self, docids):
        docs = self.env['mrp.production'].browse(docids)
        for doc in docs:
            for move in doc.move_raw_ids:
                if move.product_id:
                    combination = move.product_id.product_template_attribute_value_ids
                    description = self._get_product_multiline_description(move.product_id, combination)
                    move.product_id.display_name = description
        return super()._get_report_values(docids)

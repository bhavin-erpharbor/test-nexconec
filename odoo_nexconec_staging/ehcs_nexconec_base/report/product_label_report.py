# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import _, models
from odoo.exceptions import UserError
import re
import markupsafe


class ReportProductLabel(models.AbstractModel):
    _inherit = 'report.stock.label_product_product_view'

    def prepare_product_attr_values(self, product):
        product_name = product.name
        product_display_name = product.display_name
        if product.default_code:
            product_display_name = product.display_name.split('] ')[1]

        variant_name = product_display_name.replace(product_name, "").strip()

        words = variant_name.split()
        attr_value_list = []
        current_line = ""

        for word in words:
            # Check if adding the next word would exceed 45 chars
            if len(current_line) + len(word) + 1 <= 45:
                current_line += (" " if current_line else "") + word
            else:
                attr_value_list.append(markupsafe.Markup(current_line))
                current_line = word
        # Add the last line if it exists
        if current_line:
            attr_value_list.append(markupsafe.Markup(current_line))

        return attr_value_list

    def _get_report_values(self, docids, data):
        if data.get('active_model') == 'product.template':
            Product = self.env['product.template']
        elif data.get('active_model') == 'product.product':
            Product = self.env['product.product']
        else:
            raise UserError(_('Product model not defined, Please contact your administrator.'))

        # Retrieving the code intern from the MRP description.
        code_intern = ''
        if self.env.context.get('active_model') == 'mrp.production' and self.env.context.get('active_id'):
            mrp_production = self.env['mrp.production'].browse(int(self._context.get('active_id')))
            if mrp_production and mrp_production.product_description_variants:
                mrp_description = mrp_production.product_description_variants
                if mrp_description.startswith("Code intern:"):
                    match_string = re.search(r'Code intern:\s*(\S+)', mrp_description)
                    if match_string:
                        code_intern = match_string.group(1)


        quantity_by_product = defaultdict(list)
        for p, q in data.get('quantity_by_product').items():
            product = Product.browse(int(p))
            default_code_markup = markupsafe.Markup(product.default_code) if product.default_code else ''
            product_attr_values = self.prepare_product_attr_values(product)
            if not code_intern:
                code_intern = default_code_markup

            product_info = {
                'barcode': markupsafe.Markup(product.barcode) if product.barcode else '',
                'quantity': q,
                'display_name_markup': markupsafe.Markup(product.display_name),
                'default_code': (default_code_markup[:15], default_code_markup[15:30]),
                'product_name_markup': markupsafe.Markup(product.name),
                'product_attr_values': product_attr_values,
                'product_quantity': data.get('product_quantity') or False,
                'code_intern': markupsafe.Markup(code_intern),
            }
            quantity_by_product[product].append(product_info)
        if data.get('custom_barcodes'):
            # we expect custom barcodes to be: {product: [(barcode, qty_of_barcode)]}
            for product, barcodes_qtys in data.get('custom_barcodes').items():
                product = Product.browse(int(product))
                default_code_markup = markupsafe.Markup(product.default_code) if product.default_code else ''
                if not code_intern:
                    code_intern = default_code_markup

                for barcode_qty in barcodes_qtys:
                    quantity_by_product[product].append({
                        'barcode': markupsafe.Markup(barcode_qty[0]),
                        'quantity': barcode_qty[1],
                        'display_name_markup': markupsafe.Markup(product.display_name),
                        'default_code': (default_code_markup[:15], default_code_markup[15:30]),
                        'product_name_markup': markupsafe.Markup(product.name),
                        'product_attr_values': product_attr_values,
                        'product_quantity': data.get('product_quantity') or False,
                        'code_intern': markupsafe.Markup(code_intern),
                    }
                    )
        data['quantity'] = quantity_by_product
        layout_wizard = self.env['product.label.layout'].browse(data.get('layout_wizard'))
        data['pricelist'] = layout_wizard.pricelist_id

        return data

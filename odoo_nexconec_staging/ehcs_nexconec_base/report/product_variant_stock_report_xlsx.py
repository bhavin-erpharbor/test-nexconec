from odoo import models


class ProductVariantXLS(models.AbstractModel):
    _name = 'report.ehcs_nexconec_base.report_product_variant_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Product variant report'

    def generate_xlsx_report(self, workbook, data, lines):
        pricelist_id = data.get('pricelist')
        product_obj = self.env['product.product']
        pricelist_obj = self.env['product.pricelist']

        # Formats
        header_format = workbook.add_format({
            'font_size': 16,
            'align': 'center',
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'text_wrap': True
        })
        cell_format = workbook.add_format({
            'font_size': 15,
            'align': 'center',
            'border': 1,
            'text_wrap': True
        })
        cell_format_price = workbook.add_format({
            'font_size': 15,
            'align': 'center',
            'border': 1,
            'bold': True
        })
        cell_format_right = workbook.add_format({
            'font_size': 15,
            'align': 'right',
            'border': 1,
        })
        cell_format_right_bold = workbook.add_format({
            'font_size': 15,
            'align': 'right',
            'border': 1,
            'bold': True
        })

        sheet = workbook.add_worksheet('Product Variant')

        # Column widths
        sheet.set_column(0, 0, 30)   # Internal Reference
        sheet.set_column(1, 1, 50)   # Name
        sheet.set_column(2, 2, 80)   # Description
        sheet.set_column(3, 3, 30)   # Variant Values
        sheet.set_column(4, 4, 50)   # Category
        sheet.set_column(5, 5, 14)   # On Hand
        # Prix à partir de la colonne 6 (dynamique)

        pricelist = pricelist_obj.browse(pricelist_id)
        pricelist_items = pricelist.item_ids

        products_data = []
        for item in pricelist_items:
            minimum_qty = max(item.min_quantity, 1)
            if minimum_qty > 0:
                products_data.append({
                    'minimum_qty': minimum_qty,
                    'price': item.fixed_price
                })

        unique_products_data = sorted(
            {x['minimum_qty']: x for x in products_data}.values(),
            key=lambda x: x['minimum_qty']
        )
        minimum_qty_values = sorted(set([d['minimum_qty'] for d in unique_products_data] + [1]))

        # Headers (fixed columns)
        headers = ['Internal Reference', 'Name', 'Description', 'Variant Values', 'Category', 'On Hand']
        col = 0
        for header in headers:
            sheet.merge_range(1, col, 2, col, header, header_format)
            col += 1

        # Price headers (starting from column 6)
        price_start_col = 6
        col = price_start_col
        for minimum_qty in minimum_qty_values:
            sheet.write(1, col, 'Sales Price', cell_format_price)
            sheet.write(2, col, minimum_qty, cell_format_right_bold)
            col += 1

        # Auto-filter on headers row (row 2, from col 0 to last column)
        last_col = price_start_col + len(minimum_qty_values) - 1
        sheet.autofilter(2, 0, 2, last_col)

        # Search (comme dans ta version fonctionnelle)
        products = product_obj.search([('type', '=', 'consu'), ('qty_available', '>', 0)])

        row = 3
        for product in products:
            quantity = product.qty_available - product.outgoing_qty
            if quantity <= 0:
                continue

            # Write prices (starting from column 6)
            for idx, product_data in enumerate(unique_products_data):
                min_qty = product_data['minimum_qty']
                price = pricelist._get_product_price(product, min_qty)
                sheet.write(row, price_start_col + idx, round(price, 2), cell_format_right)

            # Fixed columns
            sheet.write(row, 0, product.default_code or product.custom_internal_reference_no_sort, cell_format)
            sheet.write(row, 1, product.name or '', cell_format)
            sheet.write(row, 2, product.description_sale or '', cell_format)
            variant_names = ", ".join([v.name for v in product.product_template_variant_value_ids])
            sheet.write(row, 3, variant_names, cell_format)

            # Category (avant On Hand)
            category_name = product.categ_id.name if product.categ_id else ''
            sheet.write(row, 4, category_name, cell_format)

            sheet.write(row, 5, quantity, cell_format_right)

            row += 1

        # Freeze panes for headers
        sheet.freeze_panes(3, 0)

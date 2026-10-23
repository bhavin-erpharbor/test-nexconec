from odoo import models, fields
from odoo.http import request
import xlsxwriter
import base64
import tempfile
import os
from io import BytesIO
from PIL import Image


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def get_xls_url(self):
        res = self.generate_quotation_xls_report()
        if res and res.get("url", False):
            return res.get("url", False)
        return "#"

    def generate_bom_xls_report(self):
        attach_obj = self.env["ir.attachment"]
        file_path = tempfile.NamedTemporaryFile().name
        workbook = xlsxwriter.Workbook(file_path + ".xlsx")
        worksheet_plan = workbook.add_worksheet("BOM Details")
        worksheet_plan.set_column(0, 0, 7)
        worksheet_plan.set_column(1, 1, 20)
        worksheet_plan.set_column(2, 2, 50)
        worksheet_plan.set_column(3, 3, 7)
        worksheet_plan.set_column(4, 4, 20)
        worksheet_plan.set_column(5, 5, 20)
        worksheet_plan.set_column(6, 6, 25)
        table_header_format = workbook.add_format(
            {
                "text_wrap": 1,
                "align": "left",
                "valign": "vcenter",
                "font_color": "black",
                "font_size": 11,
                "bold": True,
            }
        )
        no_header_format = workbook.add_format(
            {
                "text_wrap": 1,
                "align": "center",
                "valign": "vcenter",
                "font_color": "black",
                "font_group_by_lead_weeklysize": 11,
                "bold": True,
            }
        )
        no_content_format = workbook.add_format(
            {
                "text_wrap": 1,
                "align": "center",
                "valign": "vcenter",
                "font_color": "black",
                "font_size": 11,
            }
        )
        content_format = workbook.add_format(
            {
                "text_wrap": True,
                "align": "left",
                "valign": "vcenter",
                "font_color": "black",
                "font_size": 11,
            }
        )
        numerical_format = workbook.add_format(
            {
                "text_wrap": 1,
                "align": "right",
                "valign": "vcenter",
                "font_color": "black",
                "font_size": 11,
            }
        )
        url_format = workbook.add_format(
            {
                "text_wrap": 1,
                "bold": 1,
                "align": "left",
                "valign": "vcenter",
                "underline": 1,
                "font_color": "blue",
                "font_size": 12,
            }
        )

        first_row = 0
        first_col = 0
        last_row = 1
        last_col = 1
        worksheet_plan.set_row(first_row, 25)
        worksheet_plan.write(first_row, first_col, "No.", no_header_format)
        worksheet_plan.write(
            first_row, first_col + 1, "Code intern", table_header_format
        )
        worksheet_plan.write(
            first_row, first_col + 2, "Description", table_header_format
        )
        worksheet_plan.write(first_row, first_col + 3, "Qty", no_header_format)
        worksheet_plan.write(first_row, first_col + 4, "Unit Price", no_header_format)
        worksheet_plan.write(first_row, first_col + 5, "Total", no_header_format)
        worksheet_plan.write(first_row, first_col + 6, "Datasheet", table_header_format)

        count = 0
        currency_symbol = self.currency_id.symbol
        amount_untaxed = self.amount_untaxed
        amount_tax = self.amount_tax
        amount_total = self.amount_total
        bom_line_ids = 0
        for line in self.order_line:
            if line.product_id.bom_ids.bom_line_ids.product_id:
                bom_line_ids = +1
                count += 1
                code_intern = line.product_id.default_code or ""
                data_sheet_link = line.product_id.x_studio_datasheet_link_1 or ""
                description = (
                    "\n".join(
                        line.product_id.mapped("bom_ids.bom_line_ids.product_id.name")
                    )
                    or " "
                )
                qty = line.product_uom_qty
                unit_price = line.price_unit
                total = line.order_id.amount_total

                first_row += 1
                worksheet_plan.set_row(first_row, 35, content_format)
                worksheet_plan.write(first_row, first_col, count, no_content_format)
                worksheet_plan.write(
                    first_row, first_col + 1, code_intern, content_format
                )
                worksheet_plan.write(
                    first_row, first_col + 2, description, content_format
                )
                worksheet_plan.write(first_row, first_col + 3, qty, numerical_format)
                unit_price_currency = str(unit_price) + " " + currency_symbol
                worksheet_plan.write(
                    first_row, first_col + 4, unit_price_currency, numerical_format
                )
                total_currency = str(total) + " " + currency_symbol
                worksheet_plan.write(
                    first_row, first_col + 5, total_currency, numerical_format
                )
                worksheet_plan.write(
                    first_row, first_col + 6, data_sheet_link or " ", url_format
                )
        if bom_line_ids:
            first_row += 1
            worksheet_plan.set_row(first_row, 25, content_format)
            worksheet_plan.write(first_row, first_col + 4, "", table_header_format)
            worksheet_plan.write(first_row, first_col + 5, "", numerical_format)
            first_row += 1
            worksheet_plan.set_row(first_row, 25, content_format)
            worksheet_plan.write(
                first_row, first_col + 4, "Untaxed Amount", table_header_format
            )
            worksheet_plan.write(
                first_row,
                first_col + 5,
                str(amount_untaxed) + " " + currency_symbol,
                numerical_format,
            )
            first_row += 1
            worksheet_plan.set_row(first_row, 25, content_format)
            worksheet_plan.write(first_row, first_col + 4, "Taxes", table_header_format)
            worksheet_plan.write(
                first_row,
                first_col + 5,
                str(amount_tax) + " " + currency_symbol,
                numerical_format,
            )
            worksheet_plan.set_row(first_row, 25, content_format)
            worksheet_plan.write(first_row, first_col + 4, "Total", table_header_format)
            worksheet_plan.write(
                first_row,
                first_col + 5,
                str(amount_total) + " " + currency_symbol,
                numerical_format,
            )
            first_row += 1
            worksheet_plan.set_row(first_row, 25, content_format)
            worksheet_plan.write(
                first_row, first_col + 4, "Quotation #", table_header_format
            )
            worksheet_plan.write(
                first_row,
                first_col + 5,
                self.name and self.name or " ",
                numerical_format,
            )
            first_row += 1
            worksheet_plan.set_row(first_row, 25, content_format)
            worksheet_plan.write(
                first_row, first_col + 4, "Quotation Date", table_header_format
            )
            worksheet_plan.write(
                first_row,
                first_col + 5,
                self.date_order and self.date_order.strftime("%d-%m-%Y") or "",
                numerical_format,
            )
            first_row += 1
            worksheet_plan.set_row(first_row, 25, content_format)
            worksheet_plan.write(
                first_row, first_col + 4, "Expiration", table_header_format
            )
            worksheet_plan.write(
                first_row,
                first_col + 5,
                self.commitment_date
                and self.commitment_date.strftime("%d-%m-%Y")
                or " ",
                numerical_format,
            )
            first_row += 1
            worksheet_plan.set_row(first_row, 25, content_format)
            worksheet_plan.write(
                first_row, first_col + 4, "Payment Terms", table_header_format
            )
            worksheet_plan.write(
                first_row,
                first_col + 5,
                self.payment_term_id and self.payment_term_id.name or " ",
                numerical_format,
            )
            first_row += 1
            worksheet_plan.set_row(first_row, 25, content_format)
            worksheet_plan.write(
                first_row, first_col + 4, "Currency", table_header_format
            )
            worksheet_plan.write(
                first_row,
                first_col + 5,
                self.currency_id and self.currency_id.name or " ",
                numerical_format,
            )
        workbook.close()
        buf = base64.encodebytes(open(file_path + ".xlsx", "rb").read())
        try:
            if buf:
                os.remove(file_path + ".xlsx")
        except OSError:
            pass
        doc_id = attach_obj.create(
            {
                "name": "%s.xlsx" % "BOM Details Report",
                "datas": buf,
                "store_fname": "%s.xlsx" % "BOM Details Report",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % doc_id.id,
            "target": "current",
        }

    def generate_quotation_xls_report(self):
        attach_obj = self.env["ir.attachment"]
        file_path = tempfile.NamedTemporaryFile().name
        workbook = xlsxwriter.Workbook(file_path + ".xlsx")
        worksheet_plan = workbook.add_worksheet("Quotation Details")
        worksheet_plan.set_column(0, 0, 7)
        worksheet_plan.set_column(1, 1, 14)
        worksheet_plan.set_column(2, 2, 25)
        worksheet_plan.set_column(3, 3, 50)
        worksheet_plan.set_column(4, 4, 7)
        worksheet_plan.set_column(5, 5, 20)
        worksheet_plan.set_column(6, 6, 20)
        worksheet_plan.set_column(7, 7, 25)

        table_header_format = workbook.add_format(
            {
                "text_wrap": 1,
                "align": "left",
                "valign": "vcenter",
                "font_color": "black",
                "font_size": 11,
                "bold": True,
            }
        )

        no_header_format = workbook.add_format(
            {
                "text_wrap": 1,
                "align": "center",
                "valign": "vcenter",
                "font_color": "black",
                "font_size": 11,
                "bold": True,
            }
        )

        no_content_format = workbook.add_format(
            {
                "text_wrap": 1,
                "align": "center",
                "valign": "vcenter",
                "font_color": "black",
                "font_size": 11,
            }
        )

        content_format = workbook.add_format(
            {
                "text_wrap": True,
                "align": "left",
                "valign": "vcenter",
                "font_color": "black",
                "font_size": 11,
            }
        )

        numerical_format = workbook.add_format(
            {
                "text_wrap": 1,
                "align": "right",
                "valign": "vcenter",
                "font_color": "black",
                "font_size": 11,
            }
        )

        url_format = workbook.add_format(
            {
                "text_wrap": 1,
                "bold": 1,
                "align": "left",
                "valign": "vcenter",
                "underline": 1,
                "font_color": "blue",
                "font_size": 12,
            }
        )

        section_format = workbook.add_format(
            {
                "text_wrap": 1,
                "align": "left",
                "valign": "vcenter",
                "font_color": "black",
                "font_size": 12,
                "bold": True,
            }
        )

        note_format = workbook.add_format(
            {
                "text_wrap": 1,
                "align": "left",
                "valign": "vcenter",
                "font_color": "black",
                "font_size": 11,
                "italic": True,
            }
        )

        first_row = 0
        first_col = 0

        worksheet_plan.set_row(first_row, 25)
        worksheet_plan.write(first_row, first_col, "No.", no_header_format)
        worksheet_plan.write(first_row, first_col + 1, "Image", no_header_format)
        worksheet_plan.write(first_row, first_col + 2, "Code intern", table_header_format)
        worksheet_plan.write(first_row, first_col + 3, "Description", table_header_format)
        worksheet_plan.write(first_row, first_col + 4, "Qty", no_header_format)
        worksheet_plan.write(first_row, first_col + 5, "Unit Price", no_header_format)
        worksheet_plan.write(first_row, first_col + 6, "Total", no_header_format)
        worksheet_plan.write(first_row, first_col + 7, "Datasheet", table_header_format)

        count = 0
        currency_symbol = self.currency_id.symbol or ""
        amount_untaxed = self.amount_untaxed
        amount_tax = self.amount_tax
        amount_total = self.amount_total

        for line in self.order_line:
            first_row += 1

            # Manage Section line.
            # No sequence number and merge full row.
            if line.display_type == "line_section":
                worksheet_plan.set_row(first_row, 25)
                worksheet_plan.merge_range(
                    first_row,
                    first_col,
                    first_row,
                    first_col + 7,
                    line.name or "",
                    section_format,
                )
                continue

            # Manage Note line.
            # No sequence number and merge full row.
            if line.display_type == "line_note":
                worksheet_plan.set_row(first_row, 35)
                worksheet_plan.merge_range(
                    first_row,
                    first_col,
                    first_row,
                    first_col + 7,
                    line.name or "",
                    note_format,
                )
                continue

            # Skip line if no product
            if not line.product_id:
                first_row -= 1
                continue

            count += 1

            code_intern = line._get_code_intern_description() or " "
            data_sheet_link = line.product_template_id.x_studio_datasheet_link_1 or ""
            description = line.name or " "
            qty = line.product_uom_qty
            unit_price = line.price_unit
            total = line.price_subtotal

            worksheet_plan.set_row(first_row, 80, content_format)

            worksheet_plan.write(first_row, first_col, count, no_content_format)

            # Product image display properly centered in Image column
            data_uri = line.product_id.convert_image_to_jpeg_base64(
                line.product_id.image_1920
            )

            if data_uri:
                try:
                    image_bytes = base64.b64decode(data_uri)
                    image_stream = BytesIO(image_bytes)

                    # Open image using Pillow
                    image = Image.open(image_stream)

                    # Convert image to RGB for Excel compatibility
                    if image.mode != "RGB":
                        image = image.convert("RGB")

                    # Cell size settings
                    image_col_width = 14
                    row_height = 80

                    # Approximate Excel cell size in pixels
                    cell_width_px = int(image_col_width * 7 + 5)
                    cell_height_px = int(row_height * 4 / 3)

                    # Padding inside cell
                    padding = 8
                    max_width = cell_width_px - (padding * 2)
                    max_height = cell_height_px - (padding * 2)

                    # Resize image while keeping aspect ratio
                    image.thumbnail((max_width, max_height), Image.LANCZOS)

                    img_width, img_height = image.size

                    # Save resized image to stream
                    output_stream = BytesIO()
                    image.save(output_stream, format="PNG")
                    output_stream.seek(0)

                    # Calculate center offset
                    x_offset = max(0, int((cell_width_px - img_width) / 2))
                    y_offset = max(0, int((cell_height_px - img_height) / 2))

                    worksheet_plan.insert_image(
                        first_row,
                        first_col + 1,
                        "product_image.png",
                        {
                            "image_data": output_stream,
                            "x_scale": 1,
                            "y_scale": 1,
                            "x_offset": x_offset,
                            "y_offset": y_offset,
                            "object_position": 1,
                        },
                    )

                except Exception:
                    worksheet_plan.write(first_row, first_col + 1, "", content_format)
            else:
                worksheet_plan.write(first_row, first_col + 1, "", content_format)

            worksheet_plan.write(first_row, first_col + 2, code_intern, content_format)
            worksheet_plan.write(first_row, first_col + 3, description, content_format)
            worksheet_plan.write(first_row, first_col + 4, qty, numerical_format)

            unit_price_currency = str(unit_price) + " " + currency_symbol
            worksheet_plan.write(
                first_row,
                first_col + 5,
                unit_price_currency,
                numerical_format,
            )

            total_currency = str(total) + " " + currency_symbol
            worksheet_plan.write(
                first_row,
                first_col + 6,
                total_currency,
                numerical_format,
            )

            if data_sheet_link:
                worksheet_plan.write(first_row, first_col + 7, data_sheet_link, url_format)
            else:
                worksheet_plan.write(first_row, first_col + 7, " ", content_format)

        first_row += 1
        worksheet_plan.set_row(first_row, 25, content_format)
        worksheet_plan.write(first_row, first_col + 5, "", table_header_format)
        worksheet_plan.write(first_row, first_col + 6, "", numerical_format)

        first_row += 1
        worksheet_plan.set_row(first_row, 25, content_format)
        worksheet_plan.write(
            first_row,
            first_col + 5,
            "Untaxed Amount",
            table_header_format,
        )
        worksheet_plan.write(
            first_row,
            first_col + 6,
            str(amount_untaxed) + " " + currency_symbol,
            numerical_format,
        )

        first_row += 1
        worksheet_plan.set_row(first_row, 25, content_format)
        worksheet_plan.write(first_row, first_col + 5, "Taxes", table_header_format)
        worksheet_plan.write(
            first_row,
            first_col + 6,
            str(amount_tax) + " " + currency_symbol,
            numerical_format,
        )

        first_row += 1
        worksheet_plan.set_row(first_row, 25, content_format)
        worksheet_plan.write(first_row, first_col + 5, "Total", table_header_format)
        worksheet_plan.write(
            first_row,
            first_col + 6,
            str(amount_total) + " " + currency_symbol,
            numerical_format,
        )

        first_row += 1
        worksheet_plan.set_row(first_row, 25, content_format)
        worksheet_plan.write(
            first_row,
            first_col + 5,
            "Quotation #",
            table_header_format,
        )
        worksheet_plan.write(
            first_row,
            first_col + 6,
            self.name or " ",
            numerical_format,
        )

        first_row += 1
        worksheet_plan.set_row(first_row, 25, content_format)
        worksheet_plan.write(
            first_row,
            first_col + 5,
            "Quotation Date",
            table_header_format,
        )
        worksheet_plan.write(
            first_row,
            first_col + 6,
            self.date_order and self.date_order.strftime("%d-%m-%Y") or "",
            numerical_format,
        )

        first_row += 1
        worksheet_plan.set_row(first_row, 25, content_format)
        worksheet_plan.write(
            first_row,
            first_col + 5,
            "Expiration",
            table_header_format,
        )
        worksheet_plan.write(
            first_row,
            first_col + 6,
            self.commitment_date and self.commitment_date.strftime("%d-%m-%Y") or " ",
            numerical_format,
        )

        first_row += 1
        worksheet_plan.set_row(first_row, 25, content_format)
        worksheet_plan.write(
            first_row,
            first_col + 5,
            "Payment Terms",
            table_header_format,
        )
        worksheet_plan.write(
            first_row,
            first_col + 6,
            self.payment_term_id and self.payment_term_id.name or " ",
            numerical_format,
        )

        first_row += 1
        worksheet_plan.set_row(first_row, 25, content_format)
        worksheet_plan.write(
            first_row,
            first_col + 5,
            "Currency",
            table_header_format,
        )
        worksheet_plan.write(
            first_row,
            first_col + 6,
            self.currency_id and self.currency_id.name or " ",
            numerical_format,
        )

        workbook.close()

        buf = base64.encodebytes(open(file_path + ".xlsx", "rb").read())

        try:
            if buf:
                os.remove(file_path + ".xlsx")
        except OSError:
            pass

        report_name = "Quotation Details Report %s.xlsx" % (self.name or "")

        doc_id = attach_obj.sudo().create(
        {
        "name": report_name,
        "datas": buf,
        "store_fname": report_name,
        }
        )
        doc_id.public = True

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % doc_id.id,
            "target": "current",
        }

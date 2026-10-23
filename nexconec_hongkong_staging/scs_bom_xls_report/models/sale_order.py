from odoo import models, fields
import xlsxwriter
import base64
import tempfile
import os


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
        worksheet_plan.set_column(1, 1, 25)
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
        for line in self.order_line:
            count += 1
            code_intern = line._get_code_intern_description() or " "
            data_sheet_link = line.product_template_id.x_studio_datasheet_link_1 or ""
            description = line.name or " "
            qty = line.product_uom_qty
            unit_price = line.price_unit
            total = line.price_subtotal

            first_row += 1
            worksheet_plan.set_row(first_row, 35, content_format)
            worksheet_plan.write(first_row, first_col, count, no_content_format)
            worksheet_plan.set_row(first_row, 90, content_format)
            worksheet_plan.write(first_row, first_col + 1, code_intern, content_format)
            worksheet_plan.write(first_row, first_col + 2, description, content_format)
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
            first_row, first_col + 5, self.name and self.name or " ", numerical_format
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
            self.commitment_date and self.commitment_date.strftime("%d-%m-%Y") or " ",
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
        worksheet_plan.write(first_row, first_col + 4, "Currency", table_header_format)
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
                "name": "%s.xlsx" % "Quotation Details Report",
                "datas": buf,
                "store_fname": "%s.xlsx" % "Quotation Details Report",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % doc_id.id,
            "target": "current",
        }

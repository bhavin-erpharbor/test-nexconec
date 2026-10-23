from odoo import api, models, fields
import xlsxwriter
import base64
import tempfile
import os
from datetime import datetime


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    x_studio_expected_arrival = fields.Datetime(compute="_compute_studio_expected_arrival", readonly=False, store=True, string="ETA")

    @api.depends('order_line.sale_order_id', 'date_planned')
    def _compute_studio_expected_arrival(self):
        for order in self:
            if order.state == 'purchase' and order.x_studio_expected_arrival:
                continue
            order.x_studio_expected_arrival = False

    def generate_purchase_xls_report(self):
        attach_obj = self.env["ir.attachment"]
        file_path = tempfile.NamedTemporaryFile().name
        workbook = xlsxwriter.Workbook(file_path + ".xlsx")
        worksheet_plan = workbook.add_worksheet("Purchase Details")
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

        first_row = 0
        first_col = 0
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

        count = 0
        currency_symbol = self.currency_id.symbol
        amount_untaxed = self.amount_untaxed
        amount_tax = self.amount_tax
        amount_total = self.amount_total
        for line in self.order_line:
            count += 1
            code_intern = line._get_code_intern_description() or " "
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
        first_row += 1
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
            first_row, first_col + 4, "Purchase Order", table_header_format
        )
        worksheet_plan.write(
            first_row, first_col + 5, self.name and self.name or " ", numerical_format
        )
        first_row += 1
        worksheet_plan.set_row(first_row, 25, content_format)
        worksheet_plan.write(
            first_row, first_col + 4, "Purchase Date", table_header_format
        )
        worksheet_plan.write(
            first_row,
            first_col + 5,
            self.date_approve and self.date_approve.strftime("%d-%m-%Y") or "",
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
        doc_id = attach_obj.sudo().create(
            {
                "name": "%s.xlsx" % "Purchase Details Report",
                "datas": buf,
                "store_fname": "%s.xlsx" % "Purchase Details Report",
            }
        )
        doc_id.public = True
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % doc_id.id,
            "target": "current",
        }

    def write(self, vals):
        res = super().write(vals)
        if vals.get("x_studio_schedule_date"):
            for purchase_order in self.filtered(lambda p: p.state in ['purchase', 'done']):
                if purchase_order.picking_ids:
                    purchase_order.picking_ids.write({'scheduled_date': vals.get("x_studio_schedule_date")})
        if vals.get("x_studio_expected_arrival"):
            mail_template = self.env.ref(
                "ehcs_nexconec_base.nexconec_sale_order_delivery_date_eta",
                raise_if_not_found=False
            )

            sale_orders_to_check = self.env["sale.order"]

            # Get sale orders affected by changed purchase orders
            for purchase_order in self.filtered(lambda p: p.state in ["purchase", "done"]):
                sale_orders_to_check |= purchase_order._get_sale_orders()

            for sale_order in sale_orders_to_check:
                related_purchase_orders = self._get_related_purchase_orders_for_sale_order(sale_order)

                if not related_purchase_orders:
                    continue

                # If any related PO has no ETA, do NOT update Sale Order
                if any(not po.x_studio_expected_arrival for po in related_purchase_orders):
                    continue

                # All related POs have ETA now.
                # Use latest ETA from all related POs.
                final_eta = max(related_purchase_orders.mapped("x_studio_expected_arrival"))

                # Avoid duplicate write/email if same date already set
                if sale_order.commitment_date == final_eta:
                    continue

                sale_order.write({
                    "commitment_date": final_eta,
                })

                if mail_template:
                    sale_order.with_context(force_send=True).message_post_with_source(
                        mail_template,
                        subtype_xmlid="mail.mt_comment"
                    )

        return res

    def _get_related_purchase_orders_for_sale_order(self, sale_order):
        """
        Return all confirmed/done purchase orders related to this Sale Order.

        This uses purchase_order._get_sale_orders(), same as your existing logic.
        It is safe if your relation is generated through procurement/MTO flow.
        """

        purchase_orders = self.env["purchase.order"].search([
            ("state", "in", ["purchase", "done"]),
        ])

        return purchase_orders.filtered(
            lambda po: sale_order in po._get_sale_orders()
        )

    def action_auto_export_po_to_vendor(self):
        vendor = self.env.company.export_po_list_vendor_id
        if not vendor:
            return True
        if datetime.today().weekday() in [5, 6]:
            return True
        purchase_orders = self.search([
            ('partner_id', '=', vendor.id),
            ('receipt_status', 'in', ['pending', 'partial']),
        ])
        if not purchase_orders:
            return True
        sorted_purchase_orders = purchase_orders.sorted(key=lambda po: po.x_studio_expected_arrival or datetime.min, reverse=False)

        report_content, file_type = self.env['ir.actions.report']._render(
            'ehcs_nexconec_base.report_po_export_to_vendor_xlsx',
            sorted_purchase_orders.ids
        )
        filename = "PO_export_to_vendor_%s.xlsx" % datetime.today().strftime('%d_%m_%Y')
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(report_content),
            'res_model': 'purchase.order',
            'res_id': purchase_orders[0].id if purchase_orders else False,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        vendors = purchase_orders.mapped('partner_id')
        mail_template = self.env.ref('ehcs_nexconec_base.nexconec_po_export_to_vendor')
        for vendor in vendors:
            mail_template.send_mail(
                vendor.id,
                force_send=True,
                email_values={
                    'attachment_ids': [(4, attachment.id)],
                }
            )

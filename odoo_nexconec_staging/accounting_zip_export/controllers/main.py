# -*- coding: utf-8 -*-

import io
import zipfile
from collections import defaultdict

from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError

# Max number of records rendered in a single wkhtmltopdf call. Rendering a
# whole batch in one call amortizes wkhtmltopdf's process start-up cost
# (the actual bottleneck vs. one call per invoice), while still capping
# memory/time for very large date ranges.
PDF_RENDER_BATCH_SIZE = 100


class AccountingZipExportController(http.Controller):

    def _safe_filename(self, name):
        """
        Clean filename for ZIP paths.
        """
        if not name:
            return "document"

        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            name = name.replace(char, "_")

        return name.strip() or "document"

    def _render_account_moves_pdf_map(self, report_xml_id, moves):
        """
        Render invoice/bill PDFs for a whole recordset in as few
        wkhtmltopdf calls as possible (batched), instead of spawning one
        wkhtmltopdf process per record.

        Return {move_id: pdf_content}.
        """
        if not moves:
            return {}

        Report = request.env["ir.actions.report"]
        pdf_by_move_id = {}
        move_ids = moves.ids

        for offset in range(0, len(move_ids), PDF_RENDER_BATCH_SIZE):
            batch_ids = move_ids[offset:offset + PDF_RENDER_BATCH_SIZE]

            # Renders the whole batch in a single wkhtmltopdf call, then
            # splits the resulting PDF back into one stream per record
            # (same low-level primitive the core "print" / "send by email"
            # batch actions use).
            collected_streams = Report._render_qweb_pdf_prepare_streams(
                report_xml_id, {}, res_ids=batch_ids
            )

            for move_id, stream_data in collected_streams.items():
                stream = stream_data.get("stream")
                if not move_id or not stream:
                    continue
                pdf_by_move_id[move_id] = stream.getvalue()
                stream.close()

        return pdf_by_move_id

    def _add_customer_invoices_to_zip(self, wizard, zip_file, report_xml_id):
        """
        Add Customer Invoice PDFs:
        Main/Customer Invoice/

        Return True if at least one PDF added.
        """
        AccountMove = request.env["account.move"]

        domain = [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", wizard.date_from),
            ("invoice_date", "<=", wizard.date_to),
        ]

        invoices = AccountMove.search(domain)
        pdf_by_move_id = self._render_account_moves_pdf_map(report_xml_id, invoices)

        added_file = False

        for invoice in invoices:
            pdf_content = pdf_by_move_id.get(invoice.id)

            if not pdf_content:
                continue

            filename = self._safe_filename(
                invoice.name or invoice.ref or "customer_invoice"
            )

            zip_path = "Main/Customer Invoice/%s.pdf" % filename
            zip_file.writestr(zip_path, pdf_content)

            added_file = True

        return added_file

    def _add_bills_to_zip(self, wizard, zip_file, report_xml_id):
        """
        Add Vendor Bill PDFs:
        Main/Bill/

        Return True if at least one PDF added.
        """
        AccountMove = request.env["account.move"]

        domain = [
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", wizard.date_from),
            ("invoice_date", "<=", wizard.date_to),
        ]

        if wizard.exclude_partner_ids:
            domain.append(
                ("partner_id", "not in", wizard.exclude_partner_ids.ids)
            )

        bills = AccountMove.search(domain)
        pdf_by_move_id = self._render_account_moves_pdf_map(report_xml_id, bills)

        added_file = False

        for bill in bills:
            pdf_content = pdf_by_move_id.get(bill.id)

            if not pdf_content:
                continue

            filename = self._safe_filename(
                bill.name or bill.ref or "vendor_bill"
            )

            zip_path = "Main/Bill/%s.pdf" % filename
            zip_file.writestr(zip_path, pdf_content)

            added_file = True

        return added_file

    def _add_expense_attachments_to_zip(self, wizard, zip_file):
        """
        Add Expense Attachments:
        Main/Expense/

        Return True if at least one attachment added.

        If no attachment exists for selected period,
        Expense folder will NOT be created.
        """
        Expense = request.env["hr.expense"]
        Attachment = request.env["ir.attachment"]

        if "approval_date" not in Expense._fields:
            raise Exception(
                _("Field approval_date does not exist on hr.expense.")
            )

        domain = [
            ("approval_date", ">=", wizard.date_from),
            ("approval_date", "<=", wizard.date_to),
        ]

        expenses = Expense.search(domain)

        added_file = False

        if not expenses:
            return added_file

        # Single bulk search instead of one search per expense (N+1 fix).
        attachments = Attachment.search([
            ("res_model", "=", "hr.expense"),
            ("res_id", "in", expenses.ids),
            ("type", "=", "binary"),
        ])

        attachments_by_expense_id = defaultdict(list)
        for attachment in attachments:
            attachments_by_expense_id[attachment.res_id].append(attachment)

        for expense in expenses:
            employee_name = self._safe_filename(
                expense.employee_id.name or "Unknown Employee"
            )

            for attachment in attachments_by_expense_id.get(expense.id, []):
                # `raw` reads the stored bytes directly; `datas` would
                # base64-encode them first just to be decoded again below.
                file_content = attachment.raw

                if not file_content:
                    continue

                attachment_name = self._safe_filename(
                    attachment.name or "attachment"
                )

                # Folder structure:
                # Main/Expense/<Employee Name>/<Attachment>
                zip_path = "Main/Expense/%s/%s" % (
                    employee_name,
                    attachment_name,
                )

                zip_file.writestr(zip_path, file_content)

                added_file = True

        return added_file

    def _generate_zip_content(self, wizard):
        """
        Generate ZIP and return bytes.

        Folder will be created only if file exists inside it.
        """
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(
                zip_buffer,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
        ) as zip_file:

            has_any_file = False

            if wizard.is_customer_invoice:
                added_customer_invoice = self._add_customer_invoices_to_zip(
                    wizard,
                    zip_file,
                    "account.account_invoices",
                )
                if added_customer_invoice:
                    has_any_file = True

            if wizard.is_bill:
                added_bill = self._add_bills_to_zip(
                    wizard,
                    zip_file,
                    "account.action_account_original_vendor_bill",
                )
                if added_bill:
                    has_any_file = True

            if wizard.is_expense:
                added_expense = self._add_expense_attachments_to_zip(
                    wizard,
                    zip_file
                )
                if added_expense:
                    has_any_file = True

            # Optional: if nothing found, add a text file inside Main
            # so ZIP is not completely empty.
            if not has_any_file:
                zip_file.writestr(
                    "Main/No Records Found.txt",
                    "No invoice, bill, or expense attachment found for selected period."
                )

        zip_buffer.seek(0)
        return zip_buffer.read()

    @http.route(
        "/accounting_zip_export/download",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def download_accounting_zip(self, wizard_id=None, **kwargs):
        if not wizard_id:
            return request.not_found()

        wizard = request.env["accounting.zip.export.wizard"].browse(
            int(wizard_id)
        )

        if not wizard.exists():
            return request.not_found()

        try:
            wizard.check_access_rights("read")
            wizard.check_access_rule("read")
        except AccessError:
            return request.not_found()

        if wizard.date_from > wizard.date_to:
            return request.not_found()

        zip_content = self._generate_zip_content(wizard)

        filename = "Accounting_ZIP_%s_to_%s.zip" % (
            wizard.date_from,
            wizard.date_to,
        )

        headers = [
            ("Content-Type", "application/zip"),
            (
                "Content-Disposition",
                'attachment; filename="%s"' % filename,
            ),
            ("Content-Length", len(zip_content)),
        ]

        return request.make_response(
            zip_content,
            headers=headers,
        )

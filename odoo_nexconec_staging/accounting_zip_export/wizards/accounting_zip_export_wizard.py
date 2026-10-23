# -*- coding: utf-8 -*-

import base64
import io
import zipfile
from datetime import timedelta
from urllib.parse import urlencode

from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountingZipExportWizard(models.TransientModel):
    _name = "accounting.zip.export.wizard"
    _description = "Accounting ZIP Export Wizard"

    date_from = fields.Date(
        string="Date From",
        required=True,
        default=lambda self: self._default_date_from(),
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=lambda self: self._default_date_to(),
    )

    exclude_partner_ids = fields.Many2many(
        "res.partner",
        string="Exclude Vendors",
    )

    is_customer_invoice = fields.Boolean(string="Customer Invoice")
    is_bill = fields.Boolean(string="Bill")
    is_expense = fields.Boolean(string="Expense")

    def _get_previous_month_range(self):
        today = fields.Date.context_today(self)
        first_day_current_month = today.replace(day=1)
        last_day_previous_month = first_day_current_month - timedelta(days=1)
        first_day_previous_month = last_day_previous_month.replace(day=1)
        return first_day_previous_month, last_day_previous_month

    def _default_date_from(self):
        date_from, _date_to = self._get_previous_month_range()
        return date_from

    def _default_date_to(self):
        _date_from, date_to = self._get_previous_month_range()
        return date_to

    def action_export_zip(self):
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError(_("Date From cannot be greater than Date To."))

        if not self.is_customer_invoice and not self.is_bill and not self.is_expense:
            raise UserError(_("Please select at least one option."))

        params = {
            "wizard_id": self.id,
        }

        url = "/accounting_zip_export/download?%s" % urlencode(params)

        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "self",
        }

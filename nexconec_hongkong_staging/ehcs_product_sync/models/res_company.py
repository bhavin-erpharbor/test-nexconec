# -*- coding: utf-8 -*-

import xmlrpc.client
import logging

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    ehcs_product_sync_limit = fields.Integer(
        string="Product Variant Sync Limit",
        default=1,
        help="Number of France product variants to sync per click.",
    )

    ehcs_product_sync_enabled = fields.Boolean(
        string="Enable Product Sync",
        default=False,
    )

    ehcs_remote_odoo_url = fields.Char(
        string="Remote Odoo URL",
    )

    ehcs_remote_odoo_db = fields.Char(
        string="Remote Odoo Database",
    )

    ehcs_remote_odoo_username = fields.Char(
        string="Remote Odoo Username",
    )

    ehcs_remote_odoo_password = fields.Char(
        string="Remote Odoo Password",
    )

    def _ehcs_get_remote_connection(self):
        self.ensure_one()

        if not self.ehcs_remote_odoo_url:
            raise UserError(_("Remote Odoo URL is missing."))

        if not self.ehcs_remote_odoo_db:
            raise UserError(_("Remote Odoo database is missing."))

        if not self.ehcs_remote_odoo_username:
            raise UserError(_("Remote Odoo username is missing."))

        if not self.ehcs_remote_odoo_password:
            raise UserError(_("Remote Odoo password is missing."))

        url = self.ehcs_remote_odoo_url.rstrip("/")
        db = self.ehcs_remote_odoo_db
        username = self.ehcs_remote_odoo_username
        password = self.ehcs_remote_odoo_password

        try:
            common = xmlrpc.client.ServerProxy(
                "%s/xmlrpc/2/common" % url,
                allow_none=True,
            )

            uid = common.authenticate(db, username, password, {})

            if not uid:
                raise UserError(_("Remote Odoo authentication failed."))

            remote_models = xmlrpc.client.ServerProxy(
                "%s/xmlrpc/2/object" % url,
                allow_none=True,
            )

            return uid, remote_models

        except Exception as e:
            _logger.exception("EHCS remote connection failed.")
            raise UserError(_("Remote connection failed: %s") % e)

    def _ehcs_remote_execute_kw(
        self,
        model,
        method,
        args=None,
        kwargs=None,
        uid=False,
        remote_models=False,
    ):
        self.ensure_one()

        args = args or []
        kwargs = kwargs or {}

        if not uid or not remote_models:
            uid, remote_models = self._ehcs_get_remote_connection()

        try:
            return remote_models.execute_kw(
                self.ehcs_remote_odoo_db,
                uid,
                self.ehcs_remote_odoo_password,
                model,
                method,
                args,
                kwargs,
            )
        except Exception as e:
            _logger.exception(
                "EHCS remote execute failed. Model: %s Method: %s",
                model,
                method,
            )
            raise UserError(
                _("Remote execution failed for %s.%s: %s") % (model, method, e)
            )

    def ehcs_test_remote_connection(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connection Successful"),
                "message": _("Connected successfully"),
                "type": "success",
                "sticky": False,
            },
        }

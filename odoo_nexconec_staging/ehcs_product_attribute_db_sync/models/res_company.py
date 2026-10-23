import xmlrpc.client

from odoo import models, fields, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    ehcs_product_sync_enabled = fields.Boolean(
        string="Enable Product Sync",
        default=False,
    )

    ehcs_product_auto_sync_enabled = fields.Boolean(
        string="Enable Auto Sync on Product Changes",
        default=False,
        help="When enabled, only changed product/template/variant/attribute records are pushed to the remote DB automatically.",
    )

    ehcs_remote_odoo_url = fields.Char(
        string="Remote Odoo URL",
        help="Example: http://127.0.0.1:8069 or https://example.com",
    )
    ehcs_remote_odoo_db = fields.Char(string="Remote Database Name")
    ehcs_remote_odoo_username = fields.Char(string="Remote Username")
    ehcs_remote_odoo_password = fields.Char(string="Remote Password")

    def _ehcs_check_remote_config(self):
        self.ensure_one()
        if not self.ehcs_remote_odoo_url:
            raise UserError(_("Please configure Remote Odoo URL."))
        if not self.ehcs_remote_odoo_db:
            raise UserError(_("Please configure Remote Database Name."))
        if not self.ehcs_remote_odoo_username:
            raise UserError(_("Please configure Remote Username."))
        if not self.ehcs_remote_odoo_password:
            raise UserError(_("Please configure Remote Password."))

    def _ehcs_get_remote_url(self):
        self.ensure_one()
        return self.ehcs_remote_odoo_url.rstrip("/")

    def _ehcs_get_remote_connection(self):
        self.ensure_one()
        self._ehcs_check_remote_config()
        url = self._ehcs_get_remote_url()
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
        print("\n\n\ncomoo:::", url, common, self.ehcs_remote_odoo_db, self.ehcs_remote_odoo_username,
              self.ehcs_remote_odoo_password)
        uid = common.authenticate(
            self.ehcs_remote_odoo_db,
            self.ehcs_remote_odoo_username,
            self.ehcs_remote_odoo_password,
            {},
        )
        print("\n\n\nuid:::::::", uid)
        if not uid:
            raise UserError(_("Remote authentication failed. Please check credentials."))
        remote_models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)
        return uid, remote_models

    def _ehcs_remote_execute_kw(self, model, method, args=None, kwargs=None, uid=None, remote_models=None):
        self.ensure_one()
        self._ehcs_check_remote_config()
        args = args or []
        kwargs = kwargs or {}
        if not uid or not remote_models:
            uid, remote_models = self._ehcs_get_remote_connection()
        return remote_models.execute_kw(
            self.ehcs_remote_odoo_db,
            uid,
            self.ehcs_remote_odoo_password,
            model,
            method,
            args,
            kwargs,
        )

    def ehcs_test_remote_connection(self):
        self.ensure_one()
        uid, remote_models = self._ehcs_get_remote_connection()
        product_fields = self._ehcs_remote_execute_kw(
            "product.product",
            "fields_get",
            [],
            {"attributes": ["string", "type"]},
            uid=uid,
            remote_models=remote_models,
        )
        if "ehcs_source_db" not in product_fields or "ehcs_source_id" not in product_fields:
            raise UserError(_(
                "Connection works, but target sync fields are missing. "
                "Please install 'EHCS Hong Kong Product Sync Fields' in the remote database."
            ))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connection Successful"),
                "message": _("Connected successfully. Target sync fields found. Remote UID: %s") % uid,
                "type": "success",
                "sticky": False,
            },
        }

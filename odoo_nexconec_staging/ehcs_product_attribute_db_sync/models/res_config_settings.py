from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ehcs_product_sync_enabled = fields.Boolean(
        related="company_id.ehcs_product_sync_enabled",
        readonly=False,
    )
    ehcs_product_auto_sync_enabled = fields.Boolean(
        related="company_id.ehcs_product_auto_sync_enabled",
        readonly=False,
    )
    ehcs_remote_odoo_url = fields.Char(
        related="company_id.ehcs_remote_odoo_url",
        readonly=False,
    )
    ehcs_remote_odoo_db = fields.Char(
        related="company_id.ehcs_remote_odoo_db",
        readonly=False,
    )
    ehcs_remote_odoo_username = fields.Char(
        related="company_id.ehcs_remote_odoo_username",
        readonly=False,
    )
    ehcs_remote_odoo_password = fields.Char(
        related="company_id.ehcs_remote_odoo_password",
        readonly=False,
    )

    def action_ehcs_test_remote_connection(self):
        self.ensure_one()
        return self.company_id.ehcs_test_remote_connection()

    def action_ehcs_sync_product_attributes_now(self):
        self.ensure_one()
        return self.env["product.attribute"].ehcs_sync_attributes_to_remote_db(company=self.company_id)

    def action_ehcs_sync_products_now(self):
        self.ensure_one()
        return self.env["product.template"].ehcs_sync_products_to_remote_db(company=self.company_id)

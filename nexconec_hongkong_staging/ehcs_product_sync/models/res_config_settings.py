# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ehcs_product_sync_enabled = fields.Boolean(
        related="company_id.ehcs_product_sync_enabled",
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

    ehcs_product_sync_limit = fields.Integer(
        related="company_id.ehcs_product_sync_limit",
        readonly=False,
    )

    ehcs_variant_sync_progress = fields.Char(
        string="Variant Sync Progress",
        compute="_compute_ehcs_variant_sync_progress",
        readonly=True,
    )

    def _compute_ehcs_variant_sync_progress(self):
        for rec in self:
            company = rec.company_id or rec.env.company

            total = 0
            try:
                uid, remote_models = company._ehcs_get_remote_connection()

                total = company._ehcs_remote_execute_kw(
                    "product.product",
                    "search_count",
                    [[("type", "!=", "service")]],
                    {
                        "context": {
                            "active_test": True
                        }
                    },
                    uid=uid,
                    remote_models=remote_models,
                )
            except Exception:
                total = 0

            synced = rec.env["product.product"].search_count([
                ("synced_from_nexconect", "=", True),
                ("ehcs_source_id", "!=", False),
                ("type", "!=", "service"),
            ])

            rec.ehcs_variant_sync_progress = "%s / %s synced" % (synced, total)


    def action_ehcs_test_remote_connection(self):
        self.ensure_one()
        return self.company_id.ehcs_test_remote_connection()

    def action_ehcs_sync_product_attributes_now(self):
        self.ensure_one()
        return self.env["product.attribute"].ehcs_sync_attributes_to_remote_db(
            company=self.company_id,
        )

    def action_ehcs_sync_products_now(self):
        self.ensure_one()

        limit = self.company_id.ehcs_product_sync_limit or 1

        return self.env["product.product"].ehcs_sync_products_to_remote_db(
            company=self.company_id,
            limit=limit,
        )

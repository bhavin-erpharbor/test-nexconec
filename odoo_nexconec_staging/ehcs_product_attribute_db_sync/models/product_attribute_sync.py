from odoo import models, _, api, fields


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    def _ehcs_prepare_remote_attribute_vals(self):
        self.ensure_one()
        return {
            "name": self.name,
            "synced_from_nexconect": True,
            "sequence": self.sequence,
            "display_type": self.display_type,
            "create_variant": self.create_variant,
            "ehcs_source_db": self.env.cr.dbname,
            "ehcs_source_id": self.id,
        }

    def ehcs_sync_attributes_to_remote_db(self, company=None):
        companies = company or self.env["res.company"].sudo().search([("ehcs_product_sync_enabled", "=", True)])

        # Optimized: if called on records, sync only those records.
        attributes = self.sudo()
        if not attributes:
            attributes = self.env["product.attribute"].sudo().search([])

        helper = self.env["ehcs.product.sync.common"]
        for company_rec in companies:
            if not company_rec.ehcs_product_sync_enabled:
                continue
            uid, remote_models = company_rec._ehcs_get_remote_connection()
            fields_cache = {}
            helper._ehcs_assert_target_source_fields(company_rec, uid, remote_models, fields_cache)
            for attribute in attributes:
                attribute._ehcs_sync_single_attribute(company_rec, uid, remote_models, fields_cache)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sync Completed"),
                "message": _("Product attributes and values synced successfully."),
                "type": "success",
                "sticky": False,
            },
        }

    def _ehcs_sync_single_attribute(self, company, uid, remote_models, fields_cache):
        self.ensure_one()
        helper = self.env["ehcs.product.sync.common"]
        vals = self._ehcs_prepare_remote_attribute_vals()
        vals = helper._ehcs_filter_remote_vals(company, "product.attribute", vals, uid, remote_models, fields_cache)

        remote_ids = helper._ehcs_remote_search_by_source(company, "product.attribute", self.id, uid, remote_models)
        if remote_ids:
            remote_attribute_id = remote_ids[0]
            company._ehcs_remote_execute_kw(
                "product.attribute", "write", [[remote_attribute_id], vals], uid=uid, remote_models=remote_models
            )
        else:
            fallback_ids = company._ehcs_remote_execute_kw(
                "product.attribute", "search", [[("name", "=", self.name)]], {"limit": 1}, uid=uid, remote_models=remote_models
            )
            if fallback_ids:
                remote_attribute_id = fallback_ids[0]
                company._ehcs_remote_execute_kw(
                    "product.attribute", "write", [[remote_attribute_id], vals], uid=uid, remote_models=remote_models
                )
            else:
                remote_attribute_id = company._ehcs_remote_execute_kw(
                    "product.attribute", "create", [vals], uid=uid, remote_models=remote_models
                )

        for value in self.value_ids:
            value._ehcs_sync_single_attribute_value(company, remote_attribute_id, uid, remote_models, fields_cache)

    def ehcs_cron_sync_product_attributes_to_remote_db(self):
        companies = self.env["res.company"].sudo().search([("ehcs_product_sync_enabled", "=", True)])
        if companies:
            self.env["product.attribute"].sudo().ehcs_sync_attributes_to_remote_db(company=companies)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("ehcs_skip_auto_sync") and self.env.company.ehcs_product_auto_sync_enabled:
            records.with_context(ehcs_skip_auto_sync=True).ehcs_sync_attributes_to_remote_db(company=self.env.company)
        return records

    def write(self, vals):
        res = super().write(vals)
        sync_fields = {"name", "sequence", "display_type", "create_variant", "value_ids"}
        if (
            sync_fields.intersection(vals.keys())
            and not self.env.context.get("ehcs_skip_auto_sync")
            and self.env.company.ehcs_product_auto_sync_enabled
        ):
            self.with_context(ehcs_skip_auto_sync=True).ehcs_sync_attributes_to_remote_db(company=self.env.company)
        return res


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    def _ehcs_prepare_remote_attribute_value_vals(self, remote_attribute_id):
        self.ensure_one()
        vals = {
            "name": self.name,
            "attribute_id": remote_attribute_id,
            "sequence": self.sequence,
            "synced_from_nexconect": True,
            "ehcs_source_db": self.env.cr.dbname,
            "ehcs_source_id": self.id,
        }
        if "html_color" in self._fields:
            vals["html_color"] = self.html_color
        if "is_custom" in self._fields:
            vals["is_custom"] = self.is_custom
        return vals

    def _ehcs_sync_single_attribute_value(self, company, remote_attribute_id, uid, remote_models, fields_cache):
        self.ensure_one()
        helper = self.env["ehcs.product.sync.common"]
        vals = self._ehcs_prepare_remote_attribute_value_vals(remote_attribute_id)
        vals = helper._ehcs_filter_remote_vals(company, "product.attribute.value", vals, uid, remote_models, fields_cache)

        remote_ids = helper._ehcs_remote_search_by_source(company, "product.attribute.value", self.id, uid, remote_models)
        if remote_ids:
            company._ehcs_remote_execute_kw(
                "product.attribute.value", "write", [[remote_ids[0]], vals], uid=uid, remote_models=remote_models
            )
        else:
            fallback_ids = company._ehcs_remote_execute_kw(
                "product.attribute.value",
                "search",
                [[("attribute_id", "=", remote_attribute_id), ("name", "=", self.name)]],
                {"limit": 1},
                uid=uid,
                remote_models=remote_models,
            )
            if fallback_ids:
                company._ehcs_remote_execute_kw(
                    "product.attribute.value", "write", [[fallback_ids[0]], vals], uid=uid, remote_models=remote_models
                )
            else:
                company._ehcs_remote_execute_kw(
                    "product.attribute.value", "create", [vals], uid=uid, remote_models=remote_models
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("ehcs_skip_auto_sync") and self.env.company.ehcs_product_auto_sync_enabled:
            attributes = records.mapped("attribute_id")
            if attributes:
                attributes.with_context(ehcs_skip_auto_sync=True).ehcs_sync_attributes_to_remote_db(company=self.env.company)
        return records

    def write(self, vals):
        res = super().write(vals)
        sync_fields = {"name", "sequence", "html_color", "is_custom"}
        if (
            sync_fields.intersection(vals.keys())
            and not self.env.context.get("ehcs_skip_auto_sync")
            and self.env.company.ehcs_product_auto_sync_enabled
        ):
            attributes = self.mapped("attribute_id")
            if attributes:
                attributes.with_context(ehcs_skip_auto_sync=True).ehcs_sync_attributes_to_remote_db(company=self.env.company)
        return res

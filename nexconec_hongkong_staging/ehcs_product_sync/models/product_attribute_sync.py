from odoo import api, fields, models, _


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    ehcs_source_id = fields.Integer(
        string="France Source Attribute ID",
        copy=False,
        index=True,
    )
    synced_from_nexconect = fields.Boolean()

    # -------------------------------------------------------------------------
    # Prepare / Find
    # -------------------------------------------------------------------------

    def _ehcs_prepare_local_attribute_vals_from_remote(self, remote_attribute):
        vals = {
            "name": remote_attribute.get("name"),
            "sequence": remote_attribute.get("sequence", 10),
            "display_type": remote_attribute.get("display_type"),
            "create_variant": remote_attribute.get("create_variant"),
            "ehcs_source_id": remote_attribute.get("id"),
            "synced_from_nexconect": True,
        }
        return self.env["ehcs.product.sync.common"]._ehcs_filter_local_vals(
            "product.attribute",
            vals,
        )

    def _ehcs_find_local_attribute(self, remote_attribute):
        remote_id = remote_attribute.get("id")
        name = remote_attribute.get("name")

        attribute = self.search([
            ("ehcs_source_id", "=", remote_id),
            ("synced_from_nexconect", "=", True),
        ], limit=1)

        if attribute:
            return attribute

        return self.search([("name", "=", name)], limit=1)

    def _ehcs_sync_single_remote_attribute(self, remote_attribute):
        vals = self._ehcs_prepare_local_attribute_vals_from_remote(remote_attribute)
        attribute = self._ehcs_find_local_attribute(remote_attribute)

        if attribute:
            attribute.with_context(ehcs_skip_auto_sync=True).write(vals)
        else:
            attribute = self.with_context(ehcs_skip_auto_sync=True).create(vals)

        return attribute

    # -------------------------------------------------------------------------
    # Main Attribute Sync
    # -------------------------------------------------------------------------

    def ehcs_sync_attributes_to_remote_db(self, company=None):
        """
        Pull attributes + values from France DB into current Hong Kong DB.
        """
        companies = company or self.env["res.company"].sudo().search([
            ("ehcs_product_sync_enabled", "=", True),
        ])

        helper = self.env["ehcs.product.sync.common"]

        for company_rec in companies:
            if not company_rec.ehcs_product_sync_enabled:
                continue

            uid, remote_models = company_rec._ehcs_get_remote_connection()

            remote_attribute_ids = helper._ehcs_remote_search(
                company_rec,
                "product.attribute",
                [],
                uid,
                remote_models,
            )

            remote_attributes = helper._ehcs_remote_read(
                company_rec,
                "product.attribute",
                remote_attribute_ids,
                ["name", "sequence", "display_type", "create_variant"],
                uid,
                remote_models,
                context={"lang": "en_GB"}
            )

            for remote_attribute in remote_attributes:
                local_attribute = self._ehcs_sync_single_remote_attribute(remote_attribute)

                self.env["product.attribute.value"]._ehcs_sync_values_for_remote_attribute(
                    company_rec,
                    remote_attribute,
                    local_attribute,
                    uid,
                    remote_models,
                    context={"lang": "en_GB"}
                )

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

    def ehcs_cron_sync_product_attributes_to_remote_db(self):
        companies = self.env["res.company"].sudo().search([
            ("ehcs_product_sync_enabled", "=", True),
        ])
        if companies:
            self.env["product.attribute"].sudo().ehcs_sync_attributes_to_remote_db(
                company=companies
            )
        return True


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    ehcs_source_id = fields.Integer(
        string="France Source Value ID",
        copy=False,
        index=True,
    )
    synced_from_nexconect = fields.Boolean()

    # -------------------------------------------------------------------------
    # Prepare / Find
    # -------------------------------------------------------------------------

    def _ehcs_prepare_local_value_vals_from_remote(self, remote_value, local_attribute):
        vals = {
            "name": remote_value.get("name"),
            "attribute_id": local_attribute.id,
            "sequence": remote_value.get("sequence", 10),
            "ehcs_source_id": remote_value.get("id"),
            "synced_from_nexconect": True,
        }

        if "html_color" in self._fields:
            vals["html_color"] = remote_value.get("html_color")

        if "is_custom" in self._fields:
            vals["is_custom"] = remote_value.get("is_custom", False)

        return self.env["ehcs.product.sync.common"]._ehcs_filter_local_vals(
            "product.attribute.value",
            vals,
        )

    def _ehcs_find_local_value(self, remote_value, local_attribute):
        remote_id = remote_value.get("id")
        name = remote_value.get("name")

        value = self.search([
            ("ehcs_source_id", "=", remote_id),
            ("synced_from_nexconect", "=", True),
        ], limit=1)

        if value:
            return value

        return self.search([
            ("name", "=", name),
            ("attribute_id", "=", local_attribute.id),
        ], limit=1)

    def _ehcs_sync_single_remote_value(self, remote_value, local_attribute):
        vals = self._ehcs_prepare_local_value_vals_from_remote(
            remote_value,
            local_attribute,
        )

        value = self._ehcs_find_local_value(remote_value, local_attribute)

        if value:
            value.with_context(ehcs_skip_auto_sync=True).write(vals)
        else:
            value = self.with_context(ehcs_skip_auto_sync=True).create(vals)

        return value

    # -------------------------------------------------------------------------
    # Main Value Sync
    # -------------------------------------------------------------------------

    def _ehcs_sync_values_for_remote_attribute(
        self,
        company,
        remote_attribute,
        local_attribute,
        uid,
        remote_models,
        context=None
    ):
        helper = self.env["ehcs.product.sync.common"]

        remote_value_ids = helper._ehcs_remote_search(
            company,
            "product.attribute.value",
            [("attribute_id", "=", remote_attribute["id"])],
            uid,
            remote_models,
            context=context,
        )

        remote_values = helper._ehcs_remote_read(
            company,
            "product.attribute.value",
            remote_value_ids,
            ["name", "sequence", "html_color", "is_custom"],
            uid,
            remote_models,
            context=context,
        )

        for remote_value in remote_values:
            self._ehcs_sync_single_remote_value(remote_value, local_attribute)

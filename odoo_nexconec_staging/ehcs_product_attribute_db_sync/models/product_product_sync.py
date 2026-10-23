from odoo import models, _, api, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _ehcs_get_remote_nexconec_category(self, company, uid, remote_models):
        """
        Get Nexconec Brand category using XML ID (external ID) from Hong Kong DB
        """
        xmlid = "scs_customization.product_category_nexconec_brand"

        return company._ehcs_remote_execute_kw(
            "ir.model.data",
            "_xmlid_to_res_id",
            [xmlid],
            {"raise_if_not_found": True},
            uid=uid,
            remote_models=remote_models,
        )

    def _ehcs_prepare_remote_template_vals(self, company, uid, remote_models):
        self.ensure_one()

        remote_category_id = self._ehcs_get_remote_nexconec_category(
            company,
            uid,
            remote_models,
        )

        vals = {
            "name": self.name,
            "sale_ok": self.sale_ok,
            "purchase_ok": self.purchase_ok,
            "list_price": self.list_price,
            "active": self.active,
            "categ_id": remote_category_id,
            "ehcs_source_db": self.env.cr.dbname,
            "ehcs_source_id": self.id,
            "synced_from_nexconect": True
        }
        if "default_code" in self._fields:
            vals["default_code"] = self.default_code
        if "detailed_type" in self._fields:
            vals["detailed_type"] = self.detailed_type
        elif "type" in self._fields:
            vals["type"] = self.type
        return vals

    def _ehcs_prepare_remote_attribute_lines_with_connection(self, company, uid, remote_models):
        self.ensure_one()
        helper = self.env["ehcs.product.sync.common"]
        commands = []
        for line in self.attribute_line_ids:
            remote_attribute_ids = helper._ehcs_remote_search_by_source(company, "product.attribute", line.attribute_id.id, uid, remote_models)
            if not remote_attribute_ids:
                continue
            remote_attribute_id = remote_attribute_ids[0]
            remote_value_ids = []
            for value in line.value_ids:
                remote_value_found = helper._ehcs_remote_search_by_source(company, "product.attribute.value", value.id, uid, remote_models)
                if remote_value_found:
                    remote_value_ids.append(remote_value_found[0])
            if remote_value_ids:
                commands.append((0, 0, {
                    "attribute_id": remote_attribute_id,
                    "value_ids": [(6, 0, remote_value_ids)],
                }))
        return commands

    def _ehcs_sync_single_product_template(self, company, uid, remote_models, fields_cache):
        self.ensure_one()
        helper = self.env["ehcs.product.sync.common"]
        vals = self._ehcs_prepare_remote_template_vals(company, uid, remote_models)
        vals = helper._ehcs_filter_remote_vals(company, "product.template", vals, uid, remote_models, fields_cache)

        remote_ids = helper._ehcs_remote_search_by_source(company, "product.template", self.id, uid, remote_models)
        attribute_line_commands = self._ehcs_prepare_remote_attribute_lines_with_connection(company, uid, remote_models)

        if remote_ids:
            remote_template_id = remote_ids[0]
            company._ehcs_remote_execute_kw(
                "product.template", "write", [[remote_template_id], vals],
                {"context": {"active_test": False}}, uid=uid, remote_models=remote_models,
            )
        else:
            fallback_domain = [("name", "=", self.name)]
            if self.default_code:
                fallback_domain = ["|", ("default_code", "=", self.default_code), ("name", "=", self.name)]
            fallback_ids = company._ehcs_remote_execute_kw(
                "product.template", "search", [fallback_domain],
                {"limit": 1, "context": {"active_test": False}}, uid=uid, remote_models=remote_models,
            )
            if fallback_ids:
                remote_template_id = fallback_ids[0]
                company._ehcs_remote_execute_kw(
                    "product.template", "write", [[remote_template_id], vals],
                    {"context": {"active_test": False}}, uid=uid, remote_models=remote_models,
                )
            else:
                if attribute_line_commands:
                    vals["attribute_line_ids"] = attribute_line_commands
                remote_template_id = company._ehcs_remote_execute_kw(
                    "product.template", "create", [vals], uid=uid, remote_models=remote_models
                )

        # Mirror attribute lines. This lets Odoo create proper variants in target DB.
        if attribute_line_commands:
            existing_line_ids = company._ehcs_remote_execute_kw(
                "product.template.attribute.line", "search", [[("product_tmpl_id", "=", remote_template_id)]],
                {"context": {"active_test": False}}, uid=uid, remote_models=remote_models,
            )
            if existing_line_ids:
                company._ehcs_remote_execute_kw(
                    "product.template.attribute.line", "unlink", [existing_line_ids], uid=uid, remote_models=remote_models
                )
            company._ehcs_remote_execute_kw(
                "product.template", "write", [[remote_template_id], {"attribute_line_ids": attribute_line_commands}],
                {"context": {"active_test": False}}, uid=uid, remote_models=remote_models,
            )

        self._ehcs_sync_product_variants(company, remote_template_id, uid, remote_models, fields_cache)
        return remote_template_id

    def _ehcs_sync_product_variants(self, company, remote_template_id, uid, remote_models, fields_cache):
        self.ensure_one()
        for variant in self.with_context(active_test=False).product_variant_ids:
            variant._ehcs_sync_single_product_variant(company, remote_template_id, uid, remote_models, fields_cache)

    def ehcs_sync_products_to_remote_db(self, company=None):
        companies = company or self.env["res.company"].sudo().search([("ehcs_product_sync_enabled", "=", True)])

        # Optimized: if called on records, sync only those templates.
        templates = self.sudo().with_context(active_test=False)
        if not templates:
            templates = self.env["product.template"].sudo().with_context(active_test=False).search([], limit=25)

        helper = self.env["ehcs.product.sync.common"]
        for company_rec in companies:
            if not company_rec.ehcs_product_sync_enabled:
                continue
            uid, remote_models = company_rec._ehcs_get_remote_connection()
            fields_cache = {}
            helper._ehcs_assert_target_source_fields(company_rec, uid, remote_models, fields_cache)

            attributes = templates.mapped("attribute_line_ids.attribute_id")
            if attributes:
                attributes.with_context(ehcs_skip_auto_sync=True).ehcs_sync_attributes_to_remote_db(company=company_rec)

            for template in templates:
                template.with_context(ehcs_skip_auto_sync=True)._ehcs_sync_single_product_template(
                    company_rec, uid, remote_models, fields_cache
                )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sync Completed"),
                "message": _("Products, variants, attributes and values synced successfully."),
                "type": "success",
                "sticky": False,
            },
        }

    def ehcs_cron_sync_products_to_remote_db(self):
        companies = self.env["res.company"].sudo().search([("ehcs_product_sync_enabled", "=", True)])
        if companies:
            self.env["product.template"].sudo().ehcs_sync_products_to_remote_db(company=companies)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("ehcs_skip_auto_sync") and self.env.company.ehcs_product_auto_sync_enabled:
            records.with_context(ehcs_skip_auto_sync=True).ehcs_sync_products_to_remote_db(company=self.env.company)
        return records

    def write(self, vals):
        res = super().write(vals)
        sync_fields = {"name", "default_code", "sale_ok", "purchase_ok", "list_price", "active", "detailed_type", "type", "attribute_line_ids"}
        if sync_fields.intersection(vals.keys()) and not self.env.context.get("ehcs_skip_auto_sync") and self.env.company.ehcs_product_auto_sync_enabled:
            self.with_context(ehcs_skip_auto_sync=True).ehcs_sync_products_to_remote_db(company=self.env.company)
        return res


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _ehcs_prepare_remote_variant_vals(self):
        self.ensure_one()
        vals = {
            "active": self.active,
            "ehcs_source_db": self.env.cr.dbname,
            "ehcs_source_id": self.id,
        }
        if "default_code" in self._fields:
            vals["default_code"] = self.default_code
        if "barcode" in self._fields:
            vals["barcode"] = self.barcode or False
        if "lst_price" in self._fields:
            vals["lst_price"] = self.lst_price
        if "weight" in self._fields:
            vals["weight"] = self.weight
        if "volume" in self._fields:
            vals["volume"] = self.volume
        return vals

    def _ehcs_find_remote_variant_by_combination(self, company, remote_template_id, uid, remote_models):
        self.ensure_one()
        if not self.product_template_attribute_value_ids:
            remote_ids = company._ehcs_remote_execute_kw(
                "product.product", "search", [[("product_tmpl_id", "=", remote_template_id)]],
                {"limit": 1, "context": {"active_test": False}}, uid=uid, remote_models=remote_models,
            )
            return remote_ids and remote_ids[0] or False

        helper = self.env["ehcs.product.sync.common"]
        remote_ptav_ids = []
        for ptav in self.product_template_attribute_value_ids:
            remote_value_ids = helper._ehcs_remote_search_by_source(
                company, "product.attribute.value", ptav.product_attribute_value_id.id, uid, remote_models
            )
            if not remote_value_ids:
                return False
            found_ptav_ids = company._ehcs_remote_execute_kw(
                "product.template.attribute.value", "search",
                [[("product_tmpl_id", "=", remote_template_id), ("product_attribute_value_id", "=", remote_value_ids[0])]],
                {"limit": 1, "context": {"active_test": False}}, uid=uid, remote_models=remote_models,
            )
            if not found_ptav_ids:
                return False
            remote_ptav_ids.append(found_ptav_ids[0])

        domain = [("product_tmpl_id", "=", remote_template_id)]
        for remote_ptav_id in remote_ptav_ids:
            domain.append(("product_template_attribute_value_ids", "in", [remote_ptav_id]))
        remote_variant_ids = company._ehcs_remote_execute_kw(
            "product.product", "search", [domain],
            {"limit": 1, "context": {"active_test": False}}, uid=uid, remote_models=remote_models,
        )
        return remote_variant_ids and remote_variant_ids[0] or False

    def _ehcs_sync_single_product_variant(self, company, remote_template_id, uid, remote_models, fields_cache):
        self.ensure_one()
        helper = self.env["ehcs.product.sync.common"]
        vals = self._ehcs_prepare_remote_variant_vals()
        vals = helper._ehcs_filter_remote_vals(company, "product.product", vals, uid, remote_models, fields_cache)

        remote_ids = helper._ehcs_remote_search_by_source(company, "product.product", self.id, uid, remote_models)
        remote_variant_id = remote_ids and remote_ids[0] or False
        if not remote_variant_id:
            remote_variant_id = self._ehcs_find_remote_variant_by_combination(company, remote_template_id, uid, remote_models)
        if not remote_variant_id:
            return False

        company._ehcs_remote_execute_kw(
            "product.product", "write", [[remote_variant_id], vals],
            {"context": {"active_test": False}}, uid=uid, remote_models=remote_models,
        )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("ehcs_skip_auto_sync") and self.env.company.ehcs_product_auto_sync_enabled:
            templates = records.mapped("product_tmpl_id")
            if templates:
                templates.with_context(ehcs_skip_auto_sync=True).ehcs_sync_products_to_remote_db(company=self.env.company)
        return records

    def write(self, vals):
        res = super().write(vals)
        sync_fields = {"default_code", "barcode", "lst_price", "weight", "volume", "active"}
        if sync_fields.intersection(vals.keys()) and not self.env.context.get("ehcs_skip_auto_sync") and self.env.company.ehcs_product_auto_sync_enabled:
            templates = self.mapped("product_tmpl_id")
            if templates:
                templates.with_context(ehcs_skip_auto_sync=True).ehcs_sync_products_to_remote_db(company=self.env.company)
        return res

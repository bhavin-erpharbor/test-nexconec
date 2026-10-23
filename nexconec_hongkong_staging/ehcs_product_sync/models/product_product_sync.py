# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ehcs_source_id = fields.Integer(
        string="France Source Template ID",
        copy=False,
        index=True,
    )
    synced_from_nexconect = fields.Boolean()


class ProductProduct(models.Model):
    _inherit = "product.product"

    ehcs_source_id = fields.Integer(
        string="France Source Variant ID",
        index=True,
        copy=False,
    )

    synced_from_nexconect = fields.Boolean(
        string="Synced From Nexconect",
        default=False,
        copy=False,
        index=True,
    )

    # ==========================================================
    # MAIN BUTTON METHOD
    # ==========================================================

    def ehcs_sync_products_to_remote_db(self, company=False, limit=1):
        """
        Main product sync button method.

        Flow:
        Step 1: Create/update HK templates without attributes.
        Step 2: Do NOT create blank variants.
        Step 3: Apply template attributes and block auto variant creation.
        Step 4: Create/update variants with correct PTAV combination.

        Important:
        We do not create multiple blank variants because Odoo has:
            unique(product_tmpl_id, combination_indices)

        Creating blank variants gives combination_indices = '',
        which causes duplicate key error.
        """
        company = company or self.env.company
        limit = int(limit or 1)

        if not company.ehcs_product_sync_enabled:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Product Sync"),
                    "message": _("Product sync is disabled."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        uid, remote_models = company._ehcs_get_remote_connection()

        _logger.info("EHCS product sync started. Limit: %s", limit)

        sync_self = self.with_context(
            ehcs_sync_from_france=True,
            # tracking_disable=True,
            # mail_create_nolog=True,
            # mail_create_nosubscribe=True,
        )

        france_variant_ids = sync_self._ehcs_get_next_unsynced_france_variant_ids(
            company=company,
            uid=uid,
            remote_models=remote_models,
            limit=limit,
        )

        if not france_variant_ids:
            _logger.info("EHCS product sync: no unsynced France variants found.")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Product Sync"),
                    "message": _("All variants are already synced."),
                    "type": "success",
                    "sticky": False,
                },
            }

        _logger.info(
            "EHCS product sync: selected France variants: %s",
            france_variant_ids,
        )

        sync_self._ehcs_step_1_sync_templates_without_attributes(
            company=company,
            uid=uid,
            remote_models=remote_models,
            france_variant_ids=france_variant_ids,
        )

        sync_self._ehcs_step_2_skip_blank_variant_creation(
            company=company,
            uid=uid,
            remote_models=remote_models,
            france_variant_ids=france_variant_ids,
        )

        sync_self._ehcs_step_3_apply_template_attributes_block_variants(
            company=company,
            uid=uid,
            remote_models=remote_models,
            france_variant_ids=france_variant_ids,
        )

        sync_self._ehcs_step_4_create_or_update_variant_attribute_values(
            company=company,
            uid=uid,
            remote_models=remote_models,
            france_variant_ids=france_variant_ids,
        )

        synced = self.env["product.product"].search_count([
            ("synced_from_nexconect", "=", True),
            ("ehcs_source_id", "!=", False),
            ("type", "!=", "service"),
        ])

        total = company._ehcs_remote_execute_kw(
            "product.product",
            "search_count",
            [[("type", "!=", "service")]],
            {
                "context": {
                    "active_test": True,
                    "lang": "en_GB",
                }
            },
            uid=uid,
            remote_models=remote_models,
        )

        _logger.info(
            "EHCS product sync completed. Progress: %s / %s",
            synced,
            total,
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Product Sync"),
                "message": _("%s / %s variants synced.") % (synced, total),
                "type": "success",
                "sticky": False,
            },
        }

    # ==========================================================
    # REMOTE HELPER
    # ==========================================================

    def _ehcs_remote_execute(
        self,
        company,
        model,
        method,
        args=None,
        kwargs=None,
        uid=False,
        remote_models=False,
    ):
        return company._ehcs_remote_execute_kw(
            model,
            method,
            args or [],
            kwargs or {},
            uid=uid,
            remote_models=remote_models,
        )

    # ==========================================================
    # BATCH HELPER
    # ==========================================================

    def _ehcs_get_next_unsynced_france_variant_ids(
        self,
        company,
        uid,
        remote_models,
        limit=1,
    ):
        """
        Get next unsynced France product.product IDs.

        We check local HK synced variants:
            product.product.ehcs_source_id

        Then ask France DB for records whose id is not in synced list.
        """
        limit = int(limit or 1)

        synced_source_ids = self.env["product.product"].search([
            ("synced_from_nexconect", "=", True),
            ("ehcs_source_id", "!=", False),
        ]).mapped("ehcs_source_id")

        domain = [
            ("type", "!=", "service"),
        ]

        if synced_source_ids:
            domain.append(("id", "not in", synced_source_ids))

        france_variant_ids = company._ehcs_remote_execute_kw(
            "product.product",
            "search",
            [domain],
            {
                "limit": limit,
                "order": "id asc",
                "context": {
                    "active_test": True,
                    "lang": "en_GB",
                },
            },
            uid=uid,
            remote_models=remote_models,
        )

        return france_variant_ids

    # ==========================================================
    # LOCAL CATEGORY HELPER
    # ==========================================================

    def _ehcs_get_local_nexconec_category(self):
        category = self.env.ref(
            "ehcs_product_sync.product_category_nexconec_brand",
            raise_if_not_found=False,
        )
        return category.id if category else False

    # ==========================================================
    # SEARCH HELPERS
    # ==========================================================

    def _ehcs_find_local_template_by_source(self, source_template_id):
        if not source_template_id:
            return self.env["product.template"]

        return self.env["product.template"].search([
            ("ehcs_source_id", "=", source_template_id),
            ("synced_from_nexconect", "=", True),
        ], limit=1)

    def _ehcs_find_local_variant_by_source(self, source_variant_id):
        if not source_variant_id:
            return self.env["product.product"]

        return self.env["product.product"].search([
            ("ehcs_source_id", "=", source_variant_id),
            ("synced_from_nexconect", "=", True),
        ], limit=1)

    # ==========================================================
    # FIELD VALUE HELPERS
    # ==========================================================

    def _ehcs_get_m2o_id(self, value):
        """
        XML-RPC many2one usually comes like:
            [12, 'Name']
        """
        if isinstance(value, (list, tuple)) and value:
            return value[0]
        return False

    def _ehcs_prepare_template_vals(self, fr_tmpl):
        """
        Prepare product.template values.

        Important:
        - Do not pass attribute_line_ids here.
        - Category is local Nexconec category.
        - invoice_policy and type are set here.
        """
        nexconec_category_id = self._ehcs_get_local_nexconec_category()

        vals = {
            "name": fr_tmpl.get("name") or "Unnamed Product",
            "default_code": fr_tmpl.get("default_code") or False,
            "barcode": fr_tmpl.get("barcode") or False,
            "list_price": fr_tmpl.get("list_price") or 0.0,
            "standard_price": fr_tmpl.get("standard_price") or 0.0,
            "sale_ok": fr_tmpl.get("sale_ok", True),
            "purchase_ok": fr_tmpl.get("purchase_ok", True),
            "active": fr_tmpl.get("active", True),
            "description_sale": fr_tmpl.get("description_sale") or False,

            # Requested fields
            "type": fr_tmpl.get("type") or "consu",
            "invoice_policy": fr_tmpl.get("invoice_policy") or "order",

            # Sync fields
            "ehcs_source_id": fr_tmpl["id"],
            "synced_from_nexconect": True,
        }

        if nexconec_category_id:
            vals["categ_id"] = nexconec_category_id

        return vals

    def _ehcs_prepare_basic_variant_vals(self, fr_variant):
        """
        Prepare simple product.product values.

        Do not include product_tmpl_id here for existing variant write unless needed.
        Do not include PTAV values here.
        """
        return {
            "default_code": fr_variant.get("default_code") or False,
            "barcode": fr_variant.get("barcode") or False,
            "active": fr_variant.get("active", True),
            "ehcs_source_id": fr_variant["id"],
            "synced_from_nexconect": True,
        }

    # ==========================================================
    # STEP 1
    # CREATE/UPDATE TEMPLATES WITHOUT ATTRIBUTES
    # ==========================================================

    def _ehcs_step_1_sync_templates_without_attributes(
        self,
        company,
        uid,
        remote_models,
        france_variant_ids=False,
    ):
        ProductTemplate = self.env["product.template"]

        if not france_variant_ids:
            return

        france_variants = self._ehcs_remote_execute(
            company,
            "product.product",
            "read",
            [france_variant_ids],
            {
                "fields": [
                    "id",
                    "product_tmpl_id",
                ],
                "context": {
                    "active_test": True,
                    "lang": "en_GB",
                },
            },
            uid=uid,
            remote_models=remote_models,
        )

        france_template_ids = list(set([
            self._ehcs_get_m2o_id(v.get("product_tmpl_id"))
            for v in france_variants
            if self._ehcs_get_m2o_id(v.get("product_tmpl_id"))
        ]))

        if not france_template_ids:
            _logger.info("EHCS Step 1: No France template IDs found.")
            return

        france_templates = self._ehcs_remote_execute(
            company,
            "product.template",
            "read",
            [france_template_ids],
            {
                "fields": [
                    "id",
                    "name",
                    "default_code",
                    "barcode",
                    "list_price",
                    "standard_price",
                    "type",
                    "invoice_policy",
                    "sale_ok",
                    "purchase_ok",
                    "active",
                    "description_sale",
                ],
                "context": {
                    "active_test": True,
                    "lang": "en_GB",
                },
            },
            uid=uid,
            remote_models=remote_models,
        )

        _logger.info(
            "EHCS Step 1: Syncing %s templates from France.",
            len(france_templates),
        )

        for fr_tmpl in france_templates:
            hk_template = self._ehcs_find_local_template_by_source(fr_tmpl["id"])
            vals = self._ehcs_prepare_template_vals(fr_tmpl)

            # Important:
            # Do not pass attribute_line_ids here.

            if hk_template:
                hk_template.with_context(
                    ehcs_skip_auto_variant_creation=True,
                    ehcs_sync_from_france=True,
                ).write(vals)

                _logger.info(
                    "EHCS Step 1: Updated HK template %s from FR template %s.",
                    hk_template.id,
                    fr_tmpl["id"],
                )
            else:
                hk_template = ProductTemplate.with_context(
                    ehcs_skip_auto_variant_creation=True,
                    ehcs_sync_from_france=True,
                ).create(vals)

                _logger.info(
                    "EHCS Step 1: Created HK template %s from FR template %s.",
                    hk_template.id,
                    fr_tmpl["id"],
                )

    # ==========================================================
    # STEP 2
    # SKIP BLANK VARIANT CREATION
    # ==========================================================

    def _ehcs_step_2_skip_blank_variant_creation(
        self,
        company,
        uid,
        remote_models,
        france_variant_ids=False,
    ):
        """
        Step 2 intentionally does NOT create variants.

        Reason:
        Odoo product.product has unique constraint:
            unique(product_tmpl_id, combination_indices)

        If we create variants before attributes, combination_indices is empty:
            ''

        Multiple variants under same template with empty combination causes:
            product_product_combination_unique

        Therefore:
        - If a synced HK variant already exists, update its basic fields.
        - If not, skip creation.
        - Real creation happens in Step 4 with actual PTAV values.
        """
        if not france_variant_ids:
            return

        france_variants = self._ehcs_remote_execute(
            company,
            "product.product",
            "read",
            [france_variant_ids],
            {
                "fields": [
                    "id",
                    "product_tmpl_id",
                    "default_code",
                    "barcode",
                    "active",
                ],
                "context": {
                    "active_test": True,
                    "lang": "en_GB",
                },
            },
            uid=uid,
            remote_models=remote_models,
        )

        _logger.info(
            "EHCS Step 2: Skipping blank creation for %s variants.",
            len(france_variants),
        )

        for fr_variant in france_variants:
            hk_variant = self._ehcs_find_local_variant_by_source(fr_variant["id"])

            if not hk_variant:
                _logger.info(
                    "EHCS Step 2: FR variant %s will be created/linked in Step 4.",
                    fr_variant["id"],
                )
                continue

            vals = self._ehcs_prepare_basic_variant_vals(fr_variant)

            hk_variant.with_context(
                ehcs_sync_from_france=True,
                ehcs_skip_auto_variant_creation=True,
            ).write(vals)

            _logger.info(
                "EHCS Step 2: Updated existing HK variant %s from FR variant %s.",
                hk_variant.id,
                fr_variant["id"],
            )

    # ==========================================================
    # ATTRIBUTE HELPERS
    # ==========================================================

    def _ehcs_get_or_create_local_attribute(
        self,
        company,
        fr_attribute_id,
        uid,
        remote_models,
    ):
        ProductAttribute = self.env["product.attribute"]

        attribute = ProductAttribute.search([
            ("ehcs_source_id", "=", fr_attribute_id),
            ("synced_from_nexconect", "=", True),
        ], limit=1)

        if attribute:
            return attribute

        fr_attr_list = self._ehcs_remote_execute(
            company,
            "product.attribute",
            "read",
            [[fr_attribute_id]],
            {
                "fields": [
                    "id",
                    "name",
                    "display_type",
                    "create_variant",
                    "sequence",
                ],
            },
            uid=uid,
            remote_models=remote_models,
        )

        if not fr_attr_list:
            raise UserError(_("France attribute not found: %s") % fr_attribute_id)

        fr_attr = fr_attr_list[0]

        attribute = ProductAttribute.search([
            ("name", "=", fr_attr["name"]),
        ], limit=1)

        vals = {
            "name": fr_attr["name"],
            "display_type": fr_attr.get("display_type") or "radio",
            "create_variant": fr_attr.get("create_variant") or "always",
            "sequence": fr_attr.get("sequence") or 10,
            "ehcs_source_id": fr_attr["id"],
            "synced_from_nexconect": True,
        }

        if attribute:
            attribute.write(vals)
        else:
            attribute = ProductAttribute.create(vals)

        return attribute

    def _ehcs_get_or_create_local_attribute_value(
        self,
        company,
        fr_value_id,
        uid,
        remote_models,
    ):
        ProductAttributeValue = self.env["product.attribute.value"]

        value = ProductAttributeValue.search([
            ("ehcs_source_id", "=", fr_value_id),
            ("synced_from_nexconect", "=", True),
        ], limit=1)

        if value:
            return value

        fr_value_list = self._ehcs_remote_execute(
            company,
            "product.attribute.value",
            "read",
            [[fr_value_id]],
            {
                "fields": [
                    "id",
                    "name",
                    "attribute_id",
                    "sequence",
                ],
            },
            uid=uid,
            remote_models=remote_models,
        )

        if not fr_value_list:
            raise UserError(_("France attribute value not found: %s") % fr_value_id)

        fr_value = fr_value_list[0]
        fr_attribute_id = self._ehcs_get_m2o_id(fr_value.get("attribute_id"))

        attribute = self._ehcs_get_or_create_local_attribute(
            company=company,
            fr_attribute_id=fr_attribute_id,
            uid=uid,
            remote_models=remote_models,
        )

        value = ProductAttributeValue.search([
            ("name", "=", fr_value["name"]),
            ("attribute_id", "=", attribute.id),
        ], limit=1)

        vals = {
            "name": fr_value["name"],
            "attribute_id": attribute.id,
            "sequence": fr_value.get("sequence") or 10,
            "ehcs_source_id": fr_value["id"],
            "synced_from_nexconect": True,
        }

        if value:
            value.write(vals)
        else:
            value = ProductAttributeValue.create(vals)

        return value

    # ==========================================================
    # STEP 3
    # APPLY TEMPLATE ATTRIBUTES AND BLOCK NEW VARIANTS
    # ==========================================================

    def _ehcs_step_3_apply_template_attributes_block_variants(
        self,
        company,
        uid,
        remote_models,
        france_variant_ids=False,
    ):
        if not france_variant_ids:
            return

        france_variants = self._ehcs_remote_execute(
            company,
            "product.product",
            "read",
            [france_variant_ids],
            {
                "fields": [
                    "id",
                    "product_tmpl_id",
                ],
                "context": {
                    "active_test": True,
                    "lang": "en_GB",
                },
            },
            uid=uid,
            remote_models=remote_models,
        )

        france_template_ids = list(set([
            self._ehcs_get_m2o_id(v.get("product_tmpl_id"))
            for v in france_variants
            if self._ehcs_get_m2o_id(v.get("product_tmpl_id"))
        ]))

        if not france_template_ids:
            _logger.info("EHCS Step 3: No France template IDs found.")
            return

        france_templates = self._ehcs_remote_execute(
            company,
            "product.template",
            "read",
            [france_template_ids],
            {
                "fields": [
                    "id",
                    "attribute_line_ids",
                ],
                "context": {
                    "active_test": True,
                    "lang": "en_GB",
                },
            },
            uid=uid,
            remote_models=remote_models,
        )

        _logger.info(
            "EHCS Step 3: Applying attributes on %s templates.",
            len(france_templates),
        )

        for fr_tmpl in france_templates:
            try:
                with self.env.cr.savepoint():
                    hk_template = self._ehcs_find_local_template_by_source(fr_tmpl["id"])

                    if not hk_template:
                        _logger.warning(
                            "EHCS Step 3: HK template not found for FR template %s.",
                            fr_tmpl["id"],
                        )
                        continue

                    fr_line_ids = fr_tmpl.get("attribute_line_ids") or []

                    if not fr_line_ids:
                        _logger.info(
                            "EHCS Step 3: FR template %s has no attribute lines.",
                            fr_tmpl["id"],
                        )
                        continue

                    fr_lines = self._ehcs_remote_execute(
                        company,
                        "product.template.attribute.line",
                        "read",
                        [fr_line_ids],
                        {
                            "fields": [
                                "id",
                                "attribute_id",
                                "value_ids",
                            ],
                            "context": {
                                "active_test": True,
                                "lang": "en_GB",
                            },
                        },
                        uid=uid,
                        remote_models=remote_models,
                    )

                    for fr_line in fr_lines:
                        fr_attribute_id = self._ehcs_get_m2o_id(
                            fr_line.get("attribute_id")
                        )

                        if not fr_attribute_id:
                            continue

                        attribute = self._ehcs_get_or_create_local_attribute(
                            company=company,
                            fr_attribute_id=fr_attribute_id,
                            uid=uid,
                            remote_models=remote_models,
                        )

                        local_value_ids = []

                        for fr_value_id in fr_line.get("value_ids", []):
                            value = self._ehcs_get_or_create_local_attribute_value(
                                company=company,
                                fr_value_id=fr_value_id,
                                uid=uid,
                                remote_models=remote_models,
                            )
                            local_value_ids.append(value.id)

                        if not local_value_ids:
                            continue

                        self._ehcs_create_or_update_template_attribute_line(
                            hk_template=hk_template,
                            attribute=attribute,
                            local_value_ids=local_value_ids,
                        )

                    _logger.info(
                        "EHCS Step 3: Applied attributes on HK template %s from FR template %s.",
                        hk_template.id,
                        fr_tmpl["id"],
                    )

            except Exception as e:
                _logger.exception(
                    "EHCS Step 3: Failed for FR template %s. Error: %s",
                    fr_tmpl.get("id"),
                    e,
                )
                continue

    # def _ehcs_create_or_update_template_attribute_line(
    #         self,
    #         hk_template,
    #         attribute,
    #         local_value_ids,
    # ):
    #     """
    #     Safely create/update product.template.attribute.line.
    #
    #     Important:
    #     Do NOT clear all attribute_line_ids using (5, 0, 0),
    #     because it deletes attribute lines, PTAV records and may trigger
    #     product/variant recomputation or deletion.
    #     """
    #
    #     AttributeLine = self.env["product.template.attribute.line"]
    #
    #     line = AttributeLine.search([
    #         ("product_tmpl_id", "=", hk_template.id),
    #         ("attribute_id", "=", attribute.id),
    #     ], limit=1)
    #
    #     vals = {
    #         "value_ids": [(6, 0, local_value_ids)],
    #     }
    #
    #     if line:
    #         line.with_context(
    #             ehcs_skip_auto_variant_creation=True,
    #             ehcs_sync_from_france=True,
    #         ).write(vals)
    #     else:
    #         vals.update({
    #             "product_tmpl_id": hk_template.id,
    #             "attribute_id": attribute.id,
    #         })
    #
    #         line = AttributeLine.with_context(
    #             ehcs_skip_auto_variant_creation=True,
    #             ehcs_sync_from_france=True,
    #         ).create(vals)
    #
    #     return line

    def _ehcs_create_or_update_template_attribute_line(
        self,
        hk_template,
        attribute,
        local_value_ids,
    ):
        AttributeLine = self.env["product.template.attribute.line"]

        target_value_set = set(local_value_ids)

        existing_lines = AttributeLine.search([
            ("product_tmpl_id", "=", hk_template.id),
            ("attribute_id", "=", attribute.id),
        ])

        for line in existing_lines:
            existing_value_set = set(line.value_ids.ids)
            if existing_value_set == target_value_set:
                line.with_context(
                    ehcs_skip_auto_variant_creation=True,
                    ehcs_sync_from_france=True,
                ).write({
                    "value_ids": [(6, 0, local_value_ids)],
                })
                return line

        new_line = AttributeLine.with_context(
            ehcs_skip_auto_variant_creation=True,
            ehcs_sync_from_france=True,
        ).create({
            "product_tmpl_id": hk_template.id,
            "attribute_id": attribute.id,
            "value_ids": [(6, 0, local_value_ids)],
        })

        return new_line

    # ==========================================================
    # PTAV HELPER
    # ==========================================================

    def _ehcs_get_local_ptav(self, hk_template, attribute, value):
        return self.env["product.template.attribute.value"].search([
            ("product_tmpl_id", "=", hk_template.id),
            ("attribute_id", "=", attribute.id),
            ("product_attribute_value_id", "=", value.id),
        ], limit=1)

    def _ehcs_find_existing_variant_by_ptavs(self, hk_template, hk_ptav_ids):
        """
        Find existing HK variant under a template with exactly same PTAV IDs.
        """
        ProductProduct = self.env["product.product"]

        existing_variants = ProductProduct.with_context(
            active_test=False,
        ).search([
            ("product_tmpl_id", "=", hk_template.id),
        ])

        target_set = set(hk_ptav_ids)

        for variant in existing_variants:
            variant_set = set(variant.product_template_attribute_value_ids.ids)
            if variant_set == target_set:
                return variant

        return ProductProduct

    def _ehcs_find_or_create_variant_by_ptavs(
        self,
        hk_template,
        hk_ptav_ids,
        fr_variant,
    ):
        """
        Find or create HK variant using actual PTAV combination.

        This prevents duplicate empty combination_indices issue.
        """
        ProductProduct = self.env["product.product"]

        hk_variant = self._ehcs_find_local_variant_by_source(fr_variant["id"])
        if hk_variant:
            return hk_variant

        existing_variant = self._ehcs_find_existing_variant_by_ptavs(
            hk_template=hk_template,
            hk_ptav_ids=hk_ptav_ids,
        )

        if existing_variant:
            return existing_variant

        vals = {
            "product_tmpl_id": hk_template.id,
            "product_template_attribute_value_ids": [(6, 0, hk_ptav_ids)],
            "default_code": fr_variant.get("default_code") or False,
            "barcode": fr_variant.get("barcode") or False,
            "active": fr_variant.get("active", True),
            "ehcs_source_id": fr_variant["id"],
            "synced_from_nexconect": True,
        }

        hk_variant = ProductProduct.with_context(
            ehcs_sync_from_france=True,
            ehcs_skip_auto_variant_creation=True,
        ).create(vals)

        _logger.info(
            "EHCS Step 4: Created HK variant %s from FR variant %s with PTAVs %s.",
            hk_variant.id,
            fr_variant["id"],
            hk_ptav_ids,
        )

        return hk_variant

    def _ehcs_find_or_create_single_variant(
        self,
        hk_template,
        fr_variant,
    ):
        """
        For simple product / single variant product without PTAVs.

        Odoo allows only one variant with empty combination per template.
        So we reuse existing variant if present.
        """
        ProductProduct = self.env["product.product"]

        hk_variant = self._ehcs_find_local_variant_by_source(fr_variant["id"])
        if hk_variant:
            return hk_variant

        existing_variant = ProductProduct.with_context(
            active_test=False,
        ).search([
            ("product_tmpl_id", "=", hk_template.id),
        ], limit=1)

        if existing_variant:
            return existing_variant

        vals = {
            "product_tmpl_id": hk_template.id,
            "default_code": fr_variant.get("default_code") or False,
            "barcode": fr_variant.get("barcode") or False,
            "active": fr_variant.get("active", True),
            "ehcs_source_id": fr_variant["id"],
            "synced_from_nexconect": True,
        }

        hk_variant = ProductProduct.with_context(
            ehcs_sync_from_france=True,
            ehcs_skip_auto_variant_creation=True,
        ).create(vals)

        _logger.info(
            "EHCS Step 4: Created single HK variant %s from FR variant %s.",
            hk_variant.id,
            fr_variant["id"],
        )

        return hk_variant

    # ==========================================================
    # STEP 4
    # CREATE/UPDATE VARIANTS WITH ATTRIBUTE VALUES
    # ==========================================================

    def _ehcs_step_4_create_or_update_variant_attribute_values(
        self,
        company,
        uid,
        remote_models,
        france_variant_ids=False,
    ):
        if not france_variant_ids:
            return

        france_variants = self._ehcs_remote_execute(
            company,
            "product.product",
            "read",
            [france_variant_ids],
            {
                "fields": [
                    "id",
                    "product_tmpl_id",
                    "default_code",
                    "barcode",
                    "active",
                    "product_template_attribute_value_ids",
                ],
                "context": {
                    "active_test": True,
                    "lang": "en_GB",
                },
            },
            uid=uid,
            remote_models=remote_models,
        )

        _logger.info(
            "EHCS Step 4: Creating/updating %s variants with attribute values.",
            len(france_variants),
        )

        for fr_variant in france_variants:
            fr_template_id = self._ehcs_get_m2o_id(
                fr_variant.get("product_tmpl_id")
            )

            hk_template = self._ehcs_find_local_template_by_source(fr_template_id)

            if not hk_template:
                _logger.warning(
                    "EHCS Step 4: HK template not found for FR template %s. "
                    "Skipping FR variant %s.",
                    fr_template_id,
                    fr_variant["id"],
                )
                continue

            fr_ptav_ids = fr_variant.get(
                "product_template_attribute_value_ids"
            ) or []

            hk_ptav_ids = []

            if fr_ptav_ids:
                fr_ptavs = self._ehcs_remote_execute(
                    company,
                    "product.template.attribute.value",
                    "read",
                    [fr_ptav_ids],
                    {
                        "fields": [
                            "id",
                            "attribute_id",
                            "product_attribute_value_id",
                        ],
                    },
                    uid=uid,
                    remote_models=remote_models,
                )

                for fr_ptav in fr_ptavs:
                    fr_attribute_id = self._ehcs_get_m2o_id(
                        fr_ptav.get("attribute_id")
                    )
                    fr_value_id = self._ehcs_get_m2o_id(
                        fr_ptav.get("product_attribute_value_id")
                    )

                    if not fr_attribute_id or not fr_value_id:
                        continue

                    attribute = self._ehcs_get_or_create_local_attribute(
                        company=company,
                        fr_attribute_id=fr_attribute_id,
                        uid=uid,
                        remote_models=remote_models,
                    )

                    value = self._ehcs_get_or_create_local_attribute_value(
                        company=company,
                        fr_value_id=fr_value_id,
                        uid=uid,
                        remote_models=remote_models,
                    )

                    hk_ptav = self._ehcs_get_local_ptav(
                        hk_template=hk_template,
                        attribute=attribute,
                        value=value,
                    )

                    if hk_ptav:
                        hk_ptav_ids.append(hk_ptav.id)
                    else:
                        _logger.warning(
                            "EHCS Step 4: PTAV not found. "
                            "HK Template: %s, Attribute: %s, Value: %s.",
                            hk_template.id,
                            attribute.name,
                            value.name,
                        )

            try:
                if hk_ptav_ids:
                    hk_variant = self._ehcs_find_or_create_variant_by_ptavs(
                        hk_template=hk_template,
                        hk_ptav_ids=hk_ptav_ids,
                        fr_variant=fr_variant,
                    )
                else:
                    hk_variant = self._ehcs_find_or_create_single_variant(
                        hk_template=hk_template,
                        fr_variant=fr_variant,
                    )

                vals = self._ehcs_prepare_basic_variant_vals(fr_variant)

                if hk_ptav_ids:
                    vals["product_template_attribute_value_ids"] = [
                        (6, 0, hk_ptav_ids)
                    ]

                hk_variant.with_context(
                    ehcs_sync_from_france=True,
                    ehcs_skip_auto_variant_creation=True,
                ).write(vals)

                _logger.info(
                    "EHCS Step 4: Synced HK variant %s from FR variant %s.",
                    hk_variant.id,
                    fr_variant["id"],
                )

            except Exception as e:
                _logger.exception(
                    "EHCS Step 4: Could not sync FR variant %s. Error: %s",
                    fr_variant["id"],
                    e,
                )

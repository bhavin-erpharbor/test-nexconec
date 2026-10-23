# from odoo import models, _
# from odoo.exceptions import UserError
#
#
# class EhcsProductSyncCommon(models.AbstractModel):
#     _name = "ehcs.product.sync.common"
#     _description = "EHCS Product Sync Common Helpers"
#
#     # def _ehcs_source_db(self):
#     #     return self.env.cr.dbname
#
#     def _ehcs_get_remote_fields(self, company, model, uid, remote_models, fields_cache):
#         if model not in fields_cache:
#             fields_cache[model] = company._ehcs_remote_execute_kw(
#                 model,
#                 "fields_get",
#                 [],
#                 {"attributes": ["string", "type"]},
#                 uid=uid,
#                 remote_models=remote_models,
#             )
#         return fields_cache[model]
#
#     def _ehcs_filter_remote_vals(self, company, model, vals, uid, remote_models, fields_cache):
#         remote_fields = self._ehcs_get_remote_fields(company, model, uid, remote_models, fields_cache)
#         return {key: value for key, value in vals.items() if key in remote_fields}
#
#     # def _ehcs_assert_target_source_fields(self, company, uid, remote_models, fields_cache):
#     #     required_models = [
#     #         "product.attribute",
#     #         "product.attribute.value",
#     #         "product.template",
#     #         "product.product",
#     #     ]
#     #     for model in required_models:
#     #         fields = self._ehcs_get_remote_fields(company, model, uid, remote_models, fields_cache)
#     #         if "ehcs_source_db" not in fields or "ehcs_source_id" not in fields:
#     #             raise UserError(_(
#     #                 "Target database is missing sync fields on model %s. "
#     #                 "Please install 'EHCS Hong Kong Product Sync Fields' in the remote database."
#     #             ) % model)
#     #
#     # def _ehcs_remote_search_by_source(self, company, model, source_id, uid, remote_models, limit=1):
#     #     return company._ehcs_remote_execute_kw(
#     #         model,
#     #         "search",
#     #         [[
#     #             ("ehcs_source_id", "=", source_id),
#     #         ]],
#     #         {"limit": limit, "context": {"active_test": False}},
#     #         uid=uid,
#     #         remote_models=remote_models,
#     #     )
from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"


    def _create_variant_ids(self):
        """
        Block automatic variant creation during Step 3.

        When we write attribute_line_ids on product.template,
        Odoo normally creates variants automatically.

        During our sync, we only want to create/update attribute lines first.
        Variants are handled manually in Step 4.
        """
        if self.env.context.get("ehcs_skip_auto_variant_creation"):
            return True

        return super()._create_variant_ids()


class EhcsProductSyncCommon(models.AbstractModel):
    _name = "ehcs.product.sync.common"
    _description = "EHCS Product Sync Common Helpers"

    def _ehcs_get_remote_fields(self, company, model, uid, remote_models, fields_cache):
        if model not in fields_cache:
            fields_cache[model] = company._ehcs_remote_execute_kw(
                model,
                "fields_get",
                [],
                {"attributes": ["string", "type"]},
                uid=uid,
                remote_models=remote_models,
            )
        return fields_cache[model]

    def _ehcs_filter_local_vals(self, model_name, vals):
        """
        Keep only fields existing in current Hong Kong DB model.
        """
        model = self.env[model_name]
        return {
            key: value
            for key, value in vals.items()
            if key in model._fields
        }

    def _ehcs_remote_read(self, company, model, ids, fields, uid, remote_models, context=None):
        if not ids:
            return []

        return company._ehcs_remote_execute_kw(
            model,
            "read",
            [ids],
            {"fields": fields, "context": context or {}},
            uid=uid,
            remote_models=remote_models,
        )

    def _ehcs_remote_search(self, company, model, domain, uid, remote_models, limit=None, context=None):
        kwargs = {
            "context": {"active_test": False, "context": context or {}},
        }
        if limit:
            kwargs["limit"] = limit

        return company._ehcs_remote_execute_kw(
            model,
            "search",
            [domain],
            kwargs,
            uid=uid,
            remote_models=remote_models,
        )

from odoo import models, _
from odoo.exceptions import UserError


class EhcsProductSyncCommon(models.AbstractModel):
    _name = "ehcs.product.sync.common"
    _description = "EHCS Product Sync Common Helpers"

    def _ehcs_source_db(self):
        return self.env.cr.dbname

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

    def _ehcs_filter_remote_vals(self, company, model, vals, uid, remote_models, fields_cache):
        remote_fields = self._ehcs_get_remote_fields(company, model, uid, remote_models, fields_cache)
        return {key: value for key, value in vals.items() if key in remote_fields}

    def _ehcs_assert_target_source_fields(self, company, uid, remote_models, fields_cache):
        required_models = [
            "product.attribute",
            "product.attribute.value",
            "product.template",
            "product.product",
        ]
        for model in required_models:
            fields = self._ehcs_get_remote_fields(company, model, uid, remote_models, fields_cache)
            if "ehcs_source_db" not in fields or "ehcs_source_id" not in fields:
                raise UserError(_(
                    "Target database is missing sync fields on model %s. "
                    "Please install 'EHCS Hong Kong Product Sync Fields' in the remote database."
                ) % model)

    def _ehcs_remote_search_by_source(self, company, model, source_id, uid, remote_models, limit=1):
        return company._ehcs_remote_execute_kw(
            model,
            "search",
            [[
                ("ehcs_source_db", "=", self._ehcs_source_db()),
                ("ehcs_source_id", "=", source_id),
            ]],
            {"limit": limit, "context": {"active_test": False}},
            uid=uid,
            remote_models=remote_models,
        )

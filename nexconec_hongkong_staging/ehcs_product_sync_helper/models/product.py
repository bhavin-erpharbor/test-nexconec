from odoo import fields, models


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    ehcs_source_id = fields.Integer(
        string="France Source Attribute ID",
        copy=False,
        index=True,
    )

    synced_from_nexconect = fields.Boolean(
        string="Synced From Nexconect",
        copy=False,
        index=True,
    )


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    ehcs_source_id = fields.Integer(
        string="France Source Value ID",
        copy=False,
        index=True,
    )

    synced_from_nexconect = fields.Boolean(
        string="Synced From Nexconect",
        copy=False,
        index=True,
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ehcs_source_id = fields.Integer(
        string="France Source Template ID",
        copy=False,
        index=True,
    )

    synced_from_nexconect = fields.Boolean(
        string="Synced From Nexconect",
        copy=False,
        index=True,
    )

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

from odoo import api, models, fields


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    custom_cal = fields.Boolean('Enable Calculator Price')
    is_custom_attribute = fields.Boolean('Custom Variable Attribute')
    is_connector = fields.Boolean()
    is_fiber_count = fields.Boolean()


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    custom_value = fields.Float('Custom Value')
    ref_code = fields.Char('Internal Code')
    no_varient_price = fields.Float('Price', help="price for 1 meter length")



class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    custom_value = fields.Float('Custom Value', related="product_attribute_value_id.custom_value")
    ref_code = fields.Char('Internal Code', related="product_attribute_value_id.ref_code")
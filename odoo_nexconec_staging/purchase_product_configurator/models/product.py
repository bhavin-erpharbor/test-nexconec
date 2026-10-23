from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # def get_internal_ref(self, custom_val=False, combination=False):
    #     generated_code = ""
    #     if not combination:
    #         combination = self.product_template_attribute_value_ids
    #     calculator_price = 0 #len(combination.filtered(lambda l: l.attribute_id.custom_cal == True))
    #     if self.default_code:
    #         generated_code += " " + self.default_code
    #     elif self.product_tmpl_id.default_code:
    #         generated_code += " " + self.product_tmpl_id.default_code
    #     else:
    #         pass
    #     if calculator_price > 0:
    #         for attri in combination:
    #             if attri.attribute_id.is_custom_attribute:
    #                 val = float(custom_val) if custom_val else attri.custom_value
    #                 generated_code += '{0:g}'.format(val)
    #             elif attri.ref_code:
    #                 generated_code += attri.ref_code
    #             else:
    #                 pass
    #     return generated_code


    def get_product_multiline_description_sale(self):
        """ Compute a multiline description of this product, in the context of sales
                (do not use for purchases or other display reasons that don't intend to use "description_sale").
            It will often be used as the default description of a sale order line referencing this product.
        """
        name = self.name
        if self.description_sale:
            name += '\n' + self.description_sale
 
        return name



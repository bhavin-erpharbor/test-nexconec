from odoo import api, fields, models, _
from odoo.tools import get_lang


class PurchaseProductAttributeCustomValue(models.Model):
    _name = "purchase.product.attribute.custom.value"
    _description = 'Purchase Product Attribute Custom Value'
    _order = 'custom_product_template_attribute_value_id, id'

    name = fields.Char("Name", compute='_compute_name')
    custom_product_template_attribute_value_id = fields.Many2one('product.template.attribute.value', string="Attribute Value", required=True, ondelete='restrict')
    purchase_order_line_id = fields.Many2one('purchase.order.line', string="Purchase Order Line",  ondelete='cascade')
    custom_value = fields.Char("Custom Value")

    @api.depends('custom_product_template_attribute_value_id.name', 'custom_value')
    def _compute_name(self):
        for record in self:
            name = (record.custom_value or '').strip()
            if record.custom_product_template_attribute_value_id.display_name:
                name = "%s: %s" % (record.custom_product_template_attribute_value_id.display_name, name)
            record.name = name

    _sql_constraints = [
        ('sol_custom_value_unique', 'unique(custom_product_template_attribute_value_id, purchase_order_line_id)', "Only one Custom Value is allowed per Attribute Value per Sales Order Line.")
    ]


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def get_report_matrixes(self):
        """Reporting method."""
        matrixes = []
        if self.report_grids:
            grid_configured_templates = self.order_line.filtered('is_configurable_product').product_template_id.filtered(lambda ptmpl: ptmpl.product_add_mode == 'matrix')
            # TODO is configurable product and product_variant_count > 1
            # configurable products are only configured through the matrix in purchase, so no need to check product_add_mode.
            for template in grid_configured_templates:
                if len(self.order_line.filtered(lambda line: line.product_template_id == template)) > 1:
                    matrixes.append(self._get_matrix(template))
        return matrixes


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_custom_attribute_value_ids = fields.One2many('purchase.product.attribute.custom.value',
                                                          'purchase_order_line_id', 
                                                          string="Custom Values", 
                                                          copy=True)
    product_add_mode = fields.Selection(related='product_template_id.product_add_mode', depends=['product_template_id'])

    def _get_code_intern_description(self):
        combination = self.product_id.product_template_attribute_value_ids
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin
        custom_val = ""
        # for attri in self.product_custom_attribute_value_ids:
        #     if attri.custom_product_template_attribute_value_id.attribute_id.is_custom_attribute:
        #         custom_val = attri.custom_value
        if no_variant_ptavs:
            combination += no_variant_ptavs
            ptavs = sorted(combination, key=lambda x: x.attribute_id.sequence)
            combo = []
            for attri in ptavs:
                combo.append(attri.id)
            combination = self.env['product.template.attribute.value'].browse(combo)
        refcode = self.product_id.get_internal_ref(custom_val, combination=combination)
        return refcode

    def _get_variant_description(self):
        combination = self.product_id.product_template_attribute_value_ids
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin
        if no_variant_ptavs:
            combination += no_variant_ptavs
            ptavs = sorted(combination, key=lambda x: x.attribute_id.sequence)
            combo = []
            for attri in ptavs:
                combo.append(attri.id)
            combination = self.env['product.template.attribute.value'].browse(combo)
        name = ""
        lang = self.partner_id.lang
        if self.env.context.get('partner_lang'):
            lang=self.env.context.get('partner_lang')
        for attri in self.product_custom_attribute_value_ids:
            if attri.custom_product_template_attribute_value_id:
                combination = combination - attri.custom_product_template_attribute_value_id
        for ptav in combination:
            if ptav.id :
                name += "\n" + ptav.with_context(lang=lang).display_name
        for attri in self.product_custom_attribute_value_ids:
            if attri.custom_product_template_attribute_value_id:
                name += "\n" + attri.with_context(lang=lang).display_name
        return name

    def _get_productPurchase_description(self, product_lang):
        self.ensure_one()
        name = product_lang.name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase
        return name

    def _product_id_change(self):
        if not self.product_id:
            return

        self.product_uom_id = self.product_id.uom_id
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=None,
            company_id=self.company_id.id,
        )
        lang = self.partner_id.lang
        if self.env.context.get('partner_lang'):
            lang=self.env.context.get('partner_lang')
        
        name = self.with_context(partner_lang=lang)._get_code_intern_description()
        name = name + "\n" + self._get_productPurchase_description(product_lang)
        name += self.with_context(partner_lang=lang)._get_variant_description()
        self.name = name
        self._compute_tax_id()

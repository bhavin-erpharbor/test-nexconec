from odoo import api, fields, models
from lxml import etree


class ResPartner(models.Model):
    _inherit = "res.partner"

    visit_entry_ids = fields.One2many(
        comodel_name='nexconec.visit.entry',
        inverse_name='contact_id',
    )
    contact_visit_entry_ids = fields.One2many(
        comodel_name='nexconec.visit.entry',
        inverse_name='x_studio_meetings_contact',
    )
    is_default_delivery_address = fields.Boolean('Default Delivery Address?')

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id, view_type, **options)
        doc = etree.XML(result['arch'])
        if view_type == 'form' and not self.env.user.has_group('sales_team.group_sale_manager'):
            for node in doc.xpath("//field[@name='x_studio_credit_limit']"):
                node.attrib['readonly'] = '1'
                result['arch'] = etree.tostring(doc)
            for node in doc.xpath("//field[@name='property_supplier_payment_term_id']"):
                node.attrib['readonly'] = '1'
                result['arch'] = etree.tostring(doc)
        return result

from odoo import models, fields
import base64


class ProductVariant(models.TransientModel):
    _name = "product.variant.wizard"
    _description = "product info"

    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        string="Pricelist"
    )
    action = fields.Selection([
        ('print', 'Print'),
        ('send_email', 'Send Email')
    ], default='print', string='Action')
    mail_partner_ids = fields.Many2many('res.partner', string='Email CC')

    def action_generate_report(self):
        data = {
            'pricelist': self.pricelist_id.id
        }
        return self.env.ref('ehcs_nexconec_base.report_product_variant_stock_xlsx').report_action(self.id, data)

    def action_send_mail(self):
        data = {
            'pricelist': self.pricelist_id.id
        }
        ir_attachment_obj = self.env['ir.attachment'].sudo()
        ir_action_report_obj = self.env['ir.actions.report'].sudo()
        template = self.env.ref('ehcs_nexconec_base.export_variant_stock_mail_template')
        report_template_id = ir_action_report_obj._render_xlsx("ehcs_nexconec_base.report_product_variant_stock_xlsx", self.id, data=data)[0]

        # Create Attachments.
        ir_values = {
            'name': "Export Product Stock.xlsx",
            'type': 'binary',
            'datas': base64.b64encode(report_template_id),
            'store_fname': 'data_record',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }
        data_id = ir_attachment_obj.sudo().create(ir_values)
        # Add Attachment in template.
        template.attachment_ids = [(6, 0, [data_id.id])]

        cc_email_list = self.mail_partner_ids.mapped('email')
        email_cc_ids = ",".join(cc_email_list)

        email_values = {'email_to': email_cc_ids}
        template.sudo().send_mail(self.id, email_values=email_values, force_send=True)

        # Remove Attachment from template.
        template.attachment_ids = [(3, data_id.id)]
        return True

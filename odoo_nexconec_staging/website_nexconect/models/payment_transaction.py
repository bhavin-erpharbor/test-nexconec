from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _check_amount_and_confirm_order(self):
        # Overwrite to bypss the order confirmation for the stripe payments.
        confirmed_orders = self.env['sale.order']
        for tx in self:
            if len(tx.sale_order_ids) == 1:
                quotation = tx.sale_order_ids.filtered(lambda so: so.state in ('draft', 'sent'))
                if quotation and quotation._is_confirmation_amount_reached():
                    # Customisation Start.
                    if tx and tx.provider_id and tx.provider_id.code != 'stripe':
                        quotation.with_context(send_email=True).action_confirm()
                    if tx and tx.provider_id and tx.provider_id.code == 'stripe' and tx.state == 'done':
                        mail_template = self.env.ref("website_nexconect.nexconec_stripe_payment_confirmation_template")
                        if mail_template:
                            quotation.with_context(force_send=True).message_post_with_source(
                                mail_template,
                                subtype_xmlid='mail.mt_comment'
                            )
                            if quotation.state == 'draft':
                                quotation.state = 'sent'
                    # Customisation End.
                    confirmed_orders |= quotation
        return confirmed_orders

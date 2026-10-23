from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    def _get_price_available(self, order):
        """
           Override delivery price calculation.

           Purpose:
           - Calculate delivery price based on order products.
           - If the delivery method has required product tags
             in `must_have_tag_ids`, then only those order lines
             whose products contain at least one matching tag are
             considered for delivery rule calculation.
           - Products without matching tags are ignored for weight,
             volume, quantity and weight-volume calculation.

           Example:
           - Delivery Method Required Tag: Cable
           - Order Products:
               1. Loose Cable   -> Tag: Cable      -> Included
               2. Normal Product -> Tag: Other     -> Ignored
           - Delivery price rule will be calculated only using
             Loose Cable values.
        """

        self.ensure_one()
        self = self.sudo()
        order = order.sudo()
        total = weight = volume = quantity = wv = 0

        for line in order.order_line:
            if line.state == 'cancel':
                continue
            if not line.product_id or line.is_delivery:
                continue
            if line.product_id.type in {"service", "combo"}:
                continue

            product_tags = line.product_id.product_tag_ids

            # If delivery method has required tags,
            # then calculate only products having same tag
            if self.must_have_tag_ids:
                if not (product_tags & self.must_have_tag_ids):
                    continue

            qty = line.product_uom_id._compute_quantity(line.product_uom_qty, line.product_id.uom_id)

            weight += (line.product_id.weight or 0.0) * qty
            volume += (line.product_id.volume or 0.0) * qty
            wv += (line.product_id.weight or 0.0) * (line.product_id.volume or 0.0) * qty
            quantity += qty
        total = order._compute_amount_total_without_delivery()
        total = self._compute_currency(order, total, 'pricelist_to_company')

        # Important:
        # If tag-based rule is applied, use calculated tagged-product weight only.
        # Do not override with full order.shipping_weight.
        if not self.must_have_tag_ids:
            weight = self.env.context.get('order_weight') or order.shipping_weight or weight
        else:
            weight = self.env.context.get('order_weight') or weight

        return self._get_price_from_picking(total, weight, volume, quantity, wv=wv)

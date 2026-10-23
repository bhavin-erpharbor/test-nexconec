# Copyright 2017 Eficent Business and IT Consulting Services S.L.
# Copyright 2017 Serpent Consulting Services Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def copy(self, default=None):
        return super(PurchaseOrder, self.with_context(keep_line_sequence=True)).copy(
            default
        )


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    sequence_no = fields.Integer(
        string="No.",
        compute="_compute_sequence_no",
        store=False,
    )

    @api.depends(
        "order_id",
        "order_id.order_line",
        "order_id.order_line.sequence",
        "order_id.order_line.display_type",
    )
    def _compute_sequence_no(self):
        """
        Compute sequence number per purchase order.

        Section and note lines are skipped.
        Only normal purchase order lines get numbering.
        """

        # Default value for all lines
        for line in self:
            line.sequence_no = 0

        # Compute numbering per purchase order
        for order in self.mapped("order_id"):
            number = 0

            lines = order.order_line.sorted(
                key=lambda line: (line.sequence, line.id)
            )

            for line in lines:
                if line.display_type in ("line_section", "line_note"):
                    line.sequence_no = 0
                    continue

                number += 1
                line.sequence_no = number

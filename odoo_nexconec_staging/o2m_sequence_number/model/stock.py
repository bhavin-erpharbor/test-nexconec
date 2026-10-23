# -*- coding: utf-8 -*-
from odoo import models, api, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    sequence_no = fields.Integer('No.', compute="_compute_sequence_no")

    @api.depends(
        "picking_id",
        "picking_id.move_ids",
        "picking_id.move_ids.sequence",
    )
    def _compute_sequence_no(self):
        """
        Compute sequence number per picking.

        Section and note lines are skipped if stock.move has display_type field.
        Normal product moves only get numbering.
        """

        # Default value
        for move in self:
            move.sequence_no = 0

        # Compute per picking
        for picking in self.mapped("picking_id"):
            number = 0

            moves = picking.move_ids.sorted(
                key=lambda move: (move.sequence, move.id)
            )

            for move in moves:
                # Skip section/note lines if display_type field exists
                if (
                        "display_type" in move._fields
                        and move.display_type in ("line_section", "line_note")
                ):
                    move.sequence_no = 0
                    continue

                number += 1
                move.sequence_no = number


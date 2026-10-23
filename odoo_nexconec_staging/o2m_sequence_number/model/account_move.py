# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    sequence_no = fields.Integer(
        string="No.",
        compute="_compute_sequence_no",
        store=False,
    )

    @api.depends(
        "move_id",
        "move_id.invoice_line_ids",
        "move_id.invoice_line_ids.sequence",
        "move_id.invoice_line_ids.display_type",
    )
    def _compute_sequence_no(self):
        """
        Compute serial number only for normal invoice lines.

        Section and note lines will show 0/blank depending on XML/report condition.
        """

        # Default value for all lines
        for line in self:
            line.sequence_no = 1

        # Compute numbering per invoice/bill
        moves = self.mapped("move_id")

        for move in moves:
            number = 0

            # invoice_line_ids already follows invoice line order
            for line in move.invoice_line_ids.sorted(
                key=lambda l: (l.sequence, l.id)
            ):
                if line.display_type in ("line_section", "line_note"):
                    line.sequence_no = 0
                    continue

                number += 1
                line.sequence_no = number


class Message(models.Model):
    _inherit = 'mail.message'

    def check_access(self, operation):
        """
        We added this method for the 'Digest' email read operation with Admin.
        Because the 'Digest' email was sent by an Odoobot User.
        Sorry to call with SUDO.
        
        """
        for rec in self:
            if operation in ["read", "write"] and rec._name == "mail.message" and rec.author_id and rec.author_id.id == 2:
                return super(Message, self.sudo()).check_access(operation)
        return super(Message, self).check_access(operation)

# -*- coding: utf-8 -*-
from odoo import models, api, fields

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _order = "sequence"

    sequence_no = fields.Integer('No.', compute="_sequence_no")

    @api.depends('move_id.invoice_line_ids')
    def _sequence_no(self):
        for move in self:
            lines = len(move.move_id.invoice_line_ids.ids)
            move.update({'sequence_no':lines+1})
            no = 0
            for l in move.move_id.invoice_line_ids:
                no += 1
                l.sequence_no = no


class Message(models.Model):
    _inherit = 'mail.message'

    def check_access_rule(self, operation):
        """
        We added this method for the 'Digest' email read operation with Admin.
        Because the 'Digest' email was sent by an Odoobot User.
        Sorry to call with SUDO.
        
        """
        for rec in self:
            if operation in ["read", "write"] and rec._name == "mail.message" and rec.author_id and rec.author_id.id == 2:
                return super(Message, self.sudo()).check_access_rule(operation)
        return super(Message, self).check_access_rule(operation)

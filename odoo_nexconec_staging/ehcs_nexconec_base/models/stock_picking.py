from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    partner_id = fields.Many2one(tracking=1)

    def activity_schedule(self, act_type_xmlid='', date_deadline=None, summary='', note='', **act_values):
        if note and note.startswith("The delivery address has been changed on the Sales Order"):
            return True
        return super(StockPicking, self).activity_schedule(
            act_type_xmlid=act_type_xmlid, date_deadline=date_deadline, summary=summary, note=note, **act_values)

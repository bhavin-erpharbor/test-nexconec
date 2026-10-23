from odoo import fields, models


class VisitEntry(models.Model):
    _name = "nexconec.visit.entry"
    _description = "Visit Entry"
    _rec_name = "contact_id"
    _order = 'create_date desc'

    date = fields.Date(required=True)
    contact_id = fields.Many2one(
        comodel_name='res.partner',
        string="Company",
    )
    meetings_contact_id = fields.Many2one(
        comodel_name='res.partner', string="Meeting's Contact",
    )
    country_id = fields.Many2one('res.country', string="Country")
    notes = fields.Html("Meeting Notes")
    opportunities = fields.Html("Opportunities")
    challenges = fields.Html("Challenges")
    actions = fields.Html("Actions")

    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if any('create_date' in param for param in groupby):
            orderby = 'create_date desc'
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

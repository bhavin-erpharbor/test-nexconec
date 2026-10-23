from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    weekly_leads = fields.Selection([
        ('current', 'Current Week'),
        ('other', 'Others')
    ], default="current")

    def action_reset_weekly_lead(self):
        leads = self.search([('weekly_leads', '=', 'current')])
        if leads:
            leads.write({'weekly_leads': 'other'})

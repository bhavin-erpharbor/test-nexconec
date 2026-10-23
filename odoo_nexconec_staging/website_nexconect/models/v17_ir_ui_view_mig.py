from odoo import models


class View(models.Model):

    _inherit = "ir.ui.view"
    
    def _deactivate_unnecessary_views(self):
        """Added Migration script to deactivate some of unnecessary views."""
        for ir_ui_view in self:
            ir_ui_view.write({"active": False})
        return True

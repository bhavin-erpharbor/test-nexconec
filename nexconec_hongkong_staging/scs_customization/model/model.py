from odoo import api, fields, models, _
from lxml import etree


class SaleOrder(models.Model):
    _inherit = "sale.order"

    x_actualdate_jzh = fields.Datetime(
        string="DELIVERY DATE", compute="compute_x_actualdate_jzh"
    )
    x_studio_field_ys5XP = fields.Boolean(
        string="FULLY INVOICED",
    )
    x_studio_field_uhXGX = fields.Boolean(
        string="New Checkbox",
    )
    x_studio_field_TL1Uw = fields.Monetary(string="New Monetary")
    x_studio_field_TDNWN = fields.Monetary(string="X Studio Field Tdnwn")
    x_studio_field_OFw8X = fields.Monetary(string="New Monetary")
    x_attn_jzh = fields.Char(string="ATTENTION TO")
    x_delivery = fields.Char(string="DELIVERY METHOD")
    x_sale_adhoc_charge = fields.Monetary(string="Adhoc Charge")
    x_sale_final_total = fields.Monetary(
        string="Final Total", compute="compute_x_sale_final_total"
    )
    x_sale_freight = fields.Monetary(string="Freight")
    x_sale_note = fields.Text(string="NOTES")
    x_user_code = fields.Char(
        string="SALES / BUYER ID", related="user_id.x_sale_buy_id"
    )
    x_studio_credit_limit = fields.Monetary(
        string="Credit limit", related="partner_id.x_studio_credit_limit"
    )
    x_studio_delivery_contact_1 = fields.Many2one(
        "res.partner", string="Delivery Contact"
    )
    x_studio_amount_due = fields.Monetary(
        string="Amount due", related="x_studio_partner_company.total_due"
    )
    # related="x_studio_partner_company.total_due"
    x_studio_partner_company = fields.Many2one(
        "res.partner",
        string="Partner Company",
    )

    @api.depends("x_sale_freight", "amount_total", "x_sale_adhoc_charge")
    def compute_x_sale_final_total(self):
        for record in self:
            record["x_sale_final_total"] = (
                record["amount_total"]
                + record["x_sale_freight"]
                + record["x_sale_adhoc_charge"]
            )

    @api.depends("stock_reference_ids")
    def compute_x_actualdate_jzh(self):
        for order in self:
            order["x_actualdate_jzh"] = (
                self.env["stock.picking"]
                .search([("reference_ids", "in", order.stock_reference_ids.ids)], limit=1)
                .scheduled_date
                if order.stock_reference_ids
                else False
            )


class StockRule(models.Model):
    _inherit = "stock.rule"

    # def _prepare_purchase_order(self, company_id, origins, values):
    #     res = super()._prepare_purchase_order(company_id, origins, values)
    #     sale_order = self.env["sale.order"].search(
    #         [("name", "=", ", ".join(origins))], limit=1
    #     )
    #     if sale_order:
    #         res["actual_shipment_date"] = sale_order.commitment_date
    #     return res


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    name_description = fields.Text(related='name', readonly=False)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    name_description = fields.Text(related='name', readonly=False)


class HsCodeLine(models.Model):
    _name = 'hs.code.line'

    product_tmpl_id = fields.Many2one('product.template')
    partner_id = fields.Many2one('res.partner', string="Customer")
    hs_code = fields.Char(string="HS Code")


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    x_confirmed_by = fields.Many2one(
        "res.users",
        string="CONFIRMED BY",
    )
    x_studio_field_lchuJ = fields.Char(
        string="DELIVERY METHOD",
    )
    x_studio_field_UDGhw = fields.Integer(
        string="New Integer",
    )
    x_purchase_note = fields.Text(
        string="NOTES",
    )
    x_studio_field_dBmrT = fields.Many2one(
        "sale.order",
        string="Sales Order",
    )
    x_studio_so_id = fields.Many2one(
        "sale.order",
        string="Source",
    )
    actual_shipment_date = fields.Datetime(
        string="Actual Shipment Date",
    )
    x_attnpo_jzh = fields.Char(string="ATTENTION TO")
    x_purchase_adhoc_charge = fields.Monetary(string="Adhoc Charge")
    x_purchase_freight = fields.Monetary(string="Freight")
    x_user_code_po = fields.Char(
        string="SALE / BUYER ID", related="create_uid.x_sale_buy_id"
    )

    @api.depends('order_line.date_planned')
    def _compute_date_planned(self):
        """ date_planned = the earliest date_planned across all order lines. """
        for order in self:
            pass
            # dates_list = order.order_line.filtered(lambda x: not x.display_type and x.date_planned).mapped('date_planned')
            # if dates_list:
            #     order.date_planned = min(dates_list)
            # else:
            #     order.date_planned = False

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        if "actual_shipment_date" in vals:
            sale_orders_to_update = self.mapped("order_line.sale_order_id")
            for order in sale_orders_to_update:
                max_shipment_date_list = (
                    order.order_line.purchase_line_ids.order_id.filtered(
                        lambda x: x.actual_shipment_date != False
                    ).mapped("actual_shipment_date")
                )
                if max_shipment_date_list:
                    max_shipment_date = max(max_shipment_date_list)
                    if max_shipment_date:
                        order.update({"commitment_date": max_shipment_date})
                    else:
                        order.update({"commitment_date": False})
                else:
                    order.update({"commitment_date": False})
        return res


class ProductTemplate(models.Model):
    _inherit = "product.template"

    hs_code_line_ids = fields.One2many('hs.code.line', 'product_tmpl_id', string="HS Code Lines")
    x_draw_no = fields.Char(
        string="Draw No",
    )
    x_studio_field_Ip24E = fields.Text(
        string="New Multiline Text",
    )
    x_studio_hs_code = fields.Char(
        string="HS Code",
    )
    x_studio_datasheet_link_1 = fields.Char(string="Datasheet Link")

    @api.model
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        if "description_sale" in vals:
            res.write({"description_purchase": vals["description_sale"]})
        return res

    def write(self, vals):
        if "description_sale" in vals:
            vals["description_purchase"] = vals["description_sale"]

        return super(ProductTemplate, self).write(vals)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    x_currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
    )
    x_studio_field_TNwj4 = fields.Char(
        string="New Text",
    )
    x_studio_price = fields.Monetary(string="Price")


class AccountMove(models.Model):
    _inherit = "account.move"

    x_studio_awb_number = fields.Char(
        string="AWB NUMBER",
    )
    x_delivery_inv = fields.Char(string="DELIVERY METHOD")
    x_studio_field_momgh = field_name = fields.Text(
        string="NOTES",
    )


class Users(models.Model):
    _inherit = "res.users"

    x_sale_buy_id = fields.Char(string="Sales / Buyer ID")


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_studio_credit_limit = fields.Monetary(string="Credit Limit")
    visit_entry_ids = fields.One2many(
        comodel_name='nexconec.visit.entry',
        inverse_name='contact_id',
    )
    contact_visit_entry_ids = fields.One2many(
        comodel_name='nexconec.visit.entry',
        inverse_name='meetings_contact_id',
    )

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id, view_type, **options)
        doc = etree.XML(result['arch'])
        if view_type == 'form' and not self.env.user.has_group('sales_team.group_sale_manager'):
            for node in doc.xpath("//field[@name='x_studio_credit_limit']"):
                node.attrib['readonly'] = '1'
                result['arch'] = etree.tostring(doc)
            for node in doc.xpath("//field[@name='property_supplier_payment_term_id']"):
                node.attrib['readonly'] = '1'
                result['arch'] = etree.tostring(doc)
        return result

    @api.model_create_multi
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        for partner in res:
            if partner and partner.parent_id:
                partner.with_context(
                    credit_limit_update=True
                ).x_studio_credit_limit = partner.parent_id.x_studio_credit_limit
            if partner.child_ids:
                for child in partner.child_ids:
                    child.with_context(
                        credit_limit_update=True
                    ).x_studio_credit_limit = partner.x_studio_credit_limit
        return res

    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        if (
                vals
                and vals.get("x_studio_credit_limit")
                and not self.env.context.get("credit_limit_update", False)
        ):
            for partner in self:
                if partner and partner.parent_id:
                    partner.with_context(
                        credit_limit_update=True
                    ).x_studio_credit_limit = partner.parent_id.x_studio_credit_limit
                if partner.child_ids:
                    for child in partner.child_ids:
                        child.with_context(
                            credit_limit_update=True
                        ).x_studio_credit_limit = partner.x_studio_credit_limit
        return res

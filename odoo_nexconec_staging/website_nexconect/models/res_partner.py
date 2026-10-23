
import logging
from odoo import fields, models, api
from odoo.http import request
from odoo.osv import expression
from odoo.addons.website.models import ir_http


_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = "res.partner"

    public_categ_ids = fields.Many2many('product.public.category', string='Categories')
    is_without_product_attribute_description = fields.Boolean('Without Product Attribute In Description')
    is_website_cart = fields.Boolean()

    # def _compute_last_website_so_id(self):
    #     res = super(Partner, self)._compute_last_website_so_id()
    #     if self.is_website_cart:
    #         self.last_website_so_id = False
    #     return res

    @api.model_create_multi
    def create(self, vals):
        res = super(Partner, self).create(vals)
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
        res = super(Partner, self).write(vals)
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

    def _get_contact_name(self, partner, name):
        if self.env.context and self.env.context.get("only_company_name", False):
            return "%s" % (
                partner.commercial_company_name or partner.sudo().parent_id.name
            )
        return "%s, %s" % (
            partner.commercial_company_name or partner.sudo().parent_id.name,
            name,
        )

    def _get_name(self):
        """Utility method to allow name_get to be overrided without re-browse the partner"""
        partner = self
        name = partner.name or ""

        only_name = False
        if self.env.context and self.env.context.get("only_name", False):
            only_name = True
        if partner.company_name or partner.parent_id:
            if not name and partner.type in ["invoice", "delivery", "other"]:
                name = dict(self.fields_get(["type"])["type"]["selection"])[
                    partner.type
                ]
            if not partner.is_company and not only_name:
                name = self._get_contact_name(partner, name)
        if self.env.context.get("show_address_only"):
            name = partner._display_address(without_company=True)
        if self.env.context.get("show_address"):
            name = name + "\n" + partner._display_address(without_company=True)
        name = name.replace("\n\n", "\n")
        name = name.replace("\n\n", "\n")
        if self.env.context.get("address_inline"):
            splitted_names = name.split("\n")
            name = ", ".join([n for n in splitted_names if n.strip()])
        if self.env.context.get("show_email") and partner.email:
            name = "%s <%s>" % (name, partner.email)
        if self.env.context.get("html_format"):
            name = name.replace("\n", "<br/>")
        if self.env.context.get("show_vat") and partner.vat:
            name = "%s ‒ %s" % (name, partner.vat)
        return name

    @api.model
    def _name_search(self, name, domain=None, operator="ilike", limit=None, order=None):
        if (
            self.env.context.get("only_company_name", False)
            or self.env.context.get("custom_delivery", False)
            or self.env.context.get("custom_invoice", False)
            or self.env.context.get("custom_contact_delivery", False)
        ):
            domain = list(domain or [])
            # optimize out the default criterion of ``ilike ''`` that matches everything
            if not self._rec_name:
                _logger.warning(
                    "Cannot execute name_search, no _rec_name defined on %s", self._name
                )
            elif not (name == "" and operator == "ilike"):
                domain += [(self._rec_name, operator, name)]
            if self.env.context.get("only_company_name", False):
                domain += [("is_company", "=", True)]

        if self.env.context.get("me_partner_delivery") and not self.env.context.get(
            "skip_me_partner"
        ):
            me_partner_delivery = int(self._context.get("me_partner_delivery"))
            cids = [me_partner_delivery]
            if self.env.context.get("custom_invoice", False):
                inv_partner = (
                    self.with_context(skip_me_partner=1)
                    .sudo()
                    .browse(me_partner_delivery)
                )

                if inv_partner and inv_partner.parent_id:
                    me_partner_delivery = inv_partner.parent_id.id
                    cids = [me_partner_delivery]
                invoice_addresses = self.with_context(skip_me_partner=1).search(
                    [("type", "=", "invoice"), ("parent_id", "=", me_partner_delivery)],
                )
                cids = cids + invoice_addresses.ids
            if self.env.context.get("custom_delivery", False):
                delivery_partner = (
                    self.with_context(skip_me_partner=1)
                    .sudo()
                    .browse(me_partner_delivery)
                )
                if delivery_partner and delivery_partner.parent_id:
                    me_partner_delivery = delivery_partner.parent_id.id
                    cids = [me_partner_delivery]
                delivery_addresses = self.with_context(skip_me_partner=1).search(
                    [("type", "=", "delivery"), ("parent_id", "=", me_partner_delivery)]
                )
                cids = cids + delivery_addresses.ids
            if self.env.context.get("custom_contact_delivery", False):
                delivery_partner = (
                    self.with_context(skip_me_partner=1)
                    .sudo()
                    .browse(me_partner_delivery)
                )
                if delivery_partner and delivery_partner.parent_id:
                    me_partner_delivery = delivery_partner.parent_id.id
                    cids = [me_partner_delivery]
                delivery_addresses = self.with_context(skip_me_partner=1).search(
                    [
                        ("type", "!=", "delivery"),
                        ("parent_id", "=", me_partner_delivery),
                    ]
                )
                cids = cids + delivery_addresses.ids
            domain = expression.AND([domain, [("id", "in", cids)]])
        return super()._name_search(name, domain, operator, limit, order)

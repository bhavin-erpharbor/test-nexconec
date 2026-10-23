from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleExtend(WebsiteSale):

    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth="user", website=True, sitemap=WebsiteSale.sitemap_shop)
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        return super(WebsiteSaleExtend, self).shop(
            page, category, search, ppg, **post)

    @http.route(['/shop/<model("product.template"):product>'],
                type='http', auth="user", website=True,
                sitemap=True)
    def product(self, product, category=None, pricelist=None, **kwargs):
        response = super(WebsiteSaleExtend, self).product(
            product, category=category, pricelist=pricelist, **kwargs)
        return response

    @http.route(['/shop/checkout'], type='http',auth="user",
                website=True, sitemap=False)
    def checkout(self, **post):
        response = super(WebsiteSaleExtend, self).checkout(**post)
        return response

    @http.route(['/shop/cart'], type='http', auth="user",
                website=True, sitemap=False)
    def cart(self, access_token=None, revive='', **post):
        response = super(WebsiteSaleExtend, self).cart(
            access_token=access_token, revive=revive, **post)
        return response



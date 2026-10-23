from odoo.addons.sale.controllers.portal import CustomerPortal


class PortalControllerInherit(CustomerPortal):

    def _prepare_quotations_domain(self, partner):
        return [
            '|', ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('partner_id', '=', partner.id),
            ('state', 'in', ('draft', 'sent'))
        ]

    def _prepare_address_data(self, partner_sudo, **kwargs):
        """Exclut les contacts individuels (personnes physiques) de la liste des
        adresses de facturation proposées par défaut, pour ne garder que la
        société et les adresses explicitement créées comme adresses de
        facturation (type='invoice'/'other'). Un contact individuel reste
        libre de créer une nouvelle adresse de facturation manuellement."""
        address_data = super()._prepare_address_data(partner_sudo, **kwargs)

        address_data['billing_addresses'] = address_data['billing_addresses'].filtered(
            lambda p: p.is_company or p.type in ('invoice', 'other')
        )

        return address_data

# -*- coding: utf-8 -*-
"""
sale_digest.py
==============
Modèle principal du digest commercial hebdomadaire.
"""

import logging
import calendar
from datetime import date, timedelta, datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleDigest(models.Model):
    _name = 'sale.digest'
    _description = 'Digest Commercial Hebdomadaire'
    _order = 'date_start desc'

    name = fields.Char(string='Référence', compute='_compute_name', store=True)
    date_start = fields.Date(string='Début de semaine', required=True,
                             default=lambda self: date.today() - timedelta(days=7))
    date_end = fields.Date(string='Fin de semaine', required=True,
                           default=lambda self: date.today() - timedelta(days=1))
    user_ids = fields.Many2many('res.users', string='Commerciaux ciblés', domain=[('share', '=', False)])
    state = fields.Selection([('draft', 'Brouillon'), ('sent', 'Envoyé'), ('error', 'Erreur')], string='État',
                             default='draft')
    sent_count = fields.Integer(string='Emails envoyés', readonly=True)
    error_log = fields.Text(string='Journal d\'erreurs', readonly=True)

    @api.depends('date_start', 'date_end')
    def _compute_name(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                rec.name = "Digest S{} — {} au {}".format(
                    rec.date_start.isocalendar()[1],
                    rec.date_start.strftime('%d/%m/%Y'),
                    rec.date_end.strftime('%d/%m/%Y'),
                )
            else:
                rec.name = "Digest (brouillon)"

    def _get_period_dates(self):
        """Retourne toutes les dates nécessaires pour les comparaisons."""
        today = date.today()

        # Mois en cours
        month_start = today.replace(day=1)
        month_end = today

        # Mois précédent
        if month_start.month == 1:
            prev_month_start = month_start.replace(year=month_start.year - 1, month=12)
        else:
            prev_month_start = month_start.replace(month=month_start.month - 1)
        _, last_day_pm = calendar.monthrange(prev_month_start.year, prev_month_start.month)
        prev_month_end = prev_month_start.replace(day=last_day_pm)

        # Même mois l'année dernière
        month_n1_start = month_start.replace(year=month_start.year - 1)
        _, last_day_n1 = calendar.monthrange(month_n1_start.year, month_n1_start.month)
        month_n1_end = month_n1_start.replace(day=last_day_n1)

        # Année en cours
        year_start = today.replace(month=1, day=1)
        year_end = today

        # Année précédente (année complète)
        year_n1_start = today.replace(year=today.year - 1, month=1, day=1)
        year_n1_end = today.replace(year=today.year - 1, month=12, day=31)

        return {
            'month_start': month_start, 'month_end': month_end,
            'prev_month_start': prev_month_start, 'prev_month_end': prev_month_end,
            'month_n1_start': month_n1_start, 'month_n1_end': month_n1_end,
            'year_start': year_start, 'year_end': year_end,
            'year_n1_start': year_n1_start, 'year_n1_end': year_n1_end,
        }

    def _get_sales_amount(self, user, start_date, end_date):
        """Montant HT des commandes confirmées sur la période."""
        ds = datetime.combine(start_date, datetime.min.time())
        de = datetime.combine(end_date, datetime.max.time())
        orders = self.env['sale.order'].search([
            ('user_id', '=', user.id),
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', ds),
            ('date_order', '<=', de),
        ])
        total = sum(orders.mapped('amount_untaxed'))
        _logger.info("Sales amount for user %s from %s to %s: %s", user.name, start_date, end_date, total)
        return total

    def _get_invoiced_amount(self, user, start_date, end_date):
        """Montant HT des factures postées sur la période."""
        ds = datetime.combine(start_date, datetime.min.time())
        de = datetime.combine(end_date, datetime.max.time())
        invoices = self.env['account.move'].search([
            ('invoice_user_id', '=', user.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', ds.date()),
            ('invoice_date', '<=', de.date()),
        ])
        total = sum(invoices.mapped('amount_untaxed_signed'))
        _logger.info("Invoiced amount for user %s from %s to %s: %s", user.name, start_date, end_date, total)
        return total

    def _compute_opportunities(self, user):
        ds = datetime.combine(self.date_start, datetime.min.time())
        de = datetime.combine(self.date_end, datetime.max.time())

        active_opps = self.env['crm.lead'].search([
            ('user_id', '=', user.id), ('type', '=', 'opportunity'), ('active', '=', True),
        ])
        won_opps = self.env['crm.lead'].search([
            ('user_id', '=', user.id), ('type', '=', 'opportunity'),
            ('date_closed', '>=', ds), ('date_closed', '<=', de), ('probability', '=', 100),
        ])
        lost_opps = self.env['crm.lead'].with_context(active_test=False).search([
            ('user_id', '=', user.id), ('type', '=', 'opportunity'), ('active', '=', False),
            ('date_closed', '>=', ds), ('date_closed', '<=', de), ('probability', '=', 0),
        ])
        new_opps = self.env['crm.lead'].search([
            ('user_id', '=', user.id), ('type', '=', 'opportunity'),
            ('create_date', '>=', ds), ('create_date', '<=', de),
        ])

        nb_won, nb_lost = len(won_opps), len(lost_opps)
        denom = nb_won + nb_lost
        taux = round((nb_won / denom * 100) if denom else 0, 1)
        top_opps = active_opps.sorted(key=lambda o: o.expected_revenue, reverse=True)[:10]

        return {
            'nb_active': len(active_opps), 'nb_won': nb_won, 'nb_lost': nb_lost,
            'nb_new': len(new_opps), 'taux_transfo': taux, 'list_active': top_opps,
        }

    def _build_template_context(self, user):
        """Construit le dictionnaire de contexte passé au template email."""
        company = user.company_id or self.env.company
        currency = company.currency_id
        dates = self._get_period_dates()
        opps = self._compute_opportunities(user)

        # ── CA (commandes confirmées) ──
        ca_month = self._get_sales_amount(user, dates['month_start'], dates['month_end'])
        ca_prev_month = self._get_sales_amount(user, dates['prev_month_start'], dates['prev_month_end'])
        ca_month_n1 = self._get_sales_amount(user, dates['month_n1_start'], dates['month_n1_end'])
        ca_year = self._get_sales_amount(user, dates['year_start'], dates['year_end'])
        ca_year_n1 = self._get_sales_amount(user, dates['year_n1_start'], dates['year_n1_end'])

        # ── Facturation ──
        inv_month = self._get_invoiced_amount(user, dates['month_start'], dates['month_end'])
        inv_year = self._get_invoiced_amount(user, dates['year_start'], dates['year_end'])
        inv_year_n1 = self._get_invoiced_amount(user, dates['year_n1_start'], dates['year_n1_end'])

        # ── Objectifs ──
        target_month = getattr(user, 'digest_target_invoicing_month', 0) or 10000.0
        target_year = getattr(user, 'digest_target_invoicing_year', 0) or 100000.0

        _logger.info("=" * 80)
        _logger.info("BUILDING CONTEXT FOR USER: %s", user.name)
        _logger.info("CA Month: %s, CA Month N-1: %s, CA Year: %s, CA Year N-1: %s", ca_month, ca_month_n1, ca_year,
                     ca_year_n1)
        _logger.info("Inv Month: %s, Inv Year: %s, Inv Year N-1: %s", inv_month, inv_year, inv_year_n1)
        _logger.info("Targets - Month: %s, Year: %s", target_month, target_year)
        _logger.info("=" * 80)

        # ── Helpers de formatage ──
        def fmt_currency(amount):
            if amount is None or amount == 0:
                return "0 {}".format(currency.symbol)
            return "{:,.0f} {}".format(amount, currency.symbol).replace(',', ' ')

        def fmt_delta(amount):
            if amount is None:
                return "—"
            prefix = '▲ +' if amount >= 0 else '▼ '
            return "{}{}".format(prefix, fmt_currency(abs(amount)))

        def calculate_pct(val, target):
            if not target or target == 0:
                return 0.0
            return min(round((val / target) * 100, 1), 100.0)

        # ── Construction du contexte ──
        ctx = {
            # Infos générales
            'user': user,
            'company': company,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'base_url': self.env['ir.config_parameter'].sudo().get_param('web.base.url'),

            # KPI CA
            'kpi_ca': fmt_currency(ca_month),
            'kpi_ca_vs_m1': fmt_delta(ca_month - ca_prev_month),
            'kpi_ca_vs_n1': fmt_delta(ca_month - ca_month_n1),

            # Facturation vs objectif mensuel
            'facturation_mensuelle_current': fmt_currency(inv_month),
            'facturation_mensuelle_target': fmt_currency(target_month),
            'facturation_mensuelle_pct': calculate_pct(inv_month, target_month),

            # Facturation vs objectif annuel
            'facturation_annuelle_current': fmt_currency(inv_year),
            'facturation_annuelle_target': fmt_currency(target_year),
            'facturation_annuelle_pct': calculate_pct(inv_year, target_year),
            'facturation_annuelle_vs_n1': fmt_delta(inv_year - inv_year_n1),

            # Booking (détails) - utilise les mêmes données que le CA
            'booking_month': fmt_currency(ca_month),
            'booking_month_vs_n1': fmt_delta(ca_month - ca_month_n1),
            'booking_year': fmt_currency(ca_year),
            'booking_year_vs_n1': fmt_delta(ca_year - ca_year_n1),

            # Opportunités
            'opportunities': opps['list_active'],
            'nb_won': opps['nb_won'],
            'nb_lost': opps['nb_lost'],
            'nb_new_opps': opps['nb_new'],
        }

        _logger.info("CONTEXT KEYS: %s", list(ctx.keys()))
        _logger.info("BOOKING MONTH: %s", ctx.get('booking_month'))
        _logger.info("BOOKING YEAR: %s", ctx.get('booking_year'))
        _logger.info("FACTURATION ANNUELLE VS N-1: %s", ctx.get('facturation_annuelle_vs_n1'))

        return ctx

    def _get_target_users(self):
        if self.user_ids:
            return self.user_ids
        return self.env['res.users'].search([
            ('share', '=', False), ('active', '=', True), ('digest_enabled', '=', True),
        ])

    def action_send_digest(self):
        self.ensure_one()
        template = self.env.ref('sale_digest.email_template_digest', raise_if_not_found=False)
        if not template:
            raise UserError(_("Template email introuvable : sale_digest.email_template_digest"))

        users = self._get_target_users()
        sent, errors = 0, []
# petit commentaire
        for user in users:
            try:
                ctx = self._build_template_context(user)
                template.with_context(**ctx).send_mail(
                    user.id,
                    force_send=True,
                    email_values={
                        'email_to': user.email,
                        'email_from': 'Nexconec <notifications@nexconec-europe.odoo.com>',
                        'subject': "📊 Votre digest commercial — semaine du {}".format(
                            self.date_start.strftime('%d/%m/%Y')),
                        'auto_delete': False,
                    },
                )
                sent += 1
                _logger.info("Digest envoyé à %s (%s)", user.name, user.email)
            except Exception as e:
                errors.append("{} : {}".format(user.name, str(e)))
                _logger.error("Erreur digest pour %s : %s", user.name, e, exc_info=True)

        self.write({
            'state': 'error' if errors else 'sent',
            'sent_count': sent,
            'error_log': "\n".join(errors) if errors else False,
        })
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _("Digest envoyé"),
                'message': _("{} email(s) envoyé(s).{}").format(
                    sent, " {} erreur(s).".format(len(errors)) if errors else ""
                ),
                'type': 'warning' if errors else 'success',
                'sticky': bool(errors),
            },
        }

    @api.model
    def _cron_send_weekly_digest(self):
        today = date.today()
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        digest = self.create({'date_start': last_monday, 'date_end': last_sunday})
        digest.action_send_digest()
        _logger.info("Cron digest hebdomadaire terminé : %s email(s) envoyé(s).", digest.sent_count)
    # ─────────────────────────────────────────────────────────────
    # RAPPORT MENSUEL CONSOLIDÉ
    # ─────────────────────────────────────────────────────────────

    def _build_monthly_report_context(self):
        """Construit les données pour le rapport mensuel consolidé (tous commerciaux)."""
        today = date.today()
        if today.month == 1:
            report_month_start = today.replace(year=today.year - 1, month=12, day=1)
        else:
            report_month_start = today.replace(month=today.month - 1, day=1)
        _, last_day = calendar.monthrange(report_month_start.year, report_month_start.month)
        report_month_end = report_month_start.replace(day=last_day)

        company  = self.env.company
        currency = company.currency_id

        def fmt(amount):
            if not amount:
                return "0 {}".format(currency.symbol)
            return "{:,.0f} {}".format(amount, currency.symbol).replace(',', ' ')

        users = self.env['res.users'].search([
            ('share', '=', False), ('active', '=', True), ('digest_enabled', '=', True),
        ])

        rows   = []
        totals = {'ca': 0, 'invoiced': 0, 'nb_won': 0, 'nb_opps': 0}

        for user in users:
            ca  = self._get_sales_amount(user, report_month_start, report_month_end)
            inv = self._get_invoiced_amount(user, report_month_start, report_month_end)

            # Opportunités
            ds = datetime.combine(report_month_start, datetime.min.time())
            de = datetime.combine(report_month_end,   datetime.max.time())
            active_opps = self.env['crm.lead'].search([
                ('user_id', '=', user.id), ('type', '=', 'opportunity'), ('active', '=', True),
            ])
            won_opps = self.env['crm.lead'].search([
                ('user_id', '=', user.id), ('type', '=', 'opportunity'),
                ('date_closed', '>=', ds), ('date_closed', '<=', de), ('probability', '=', 100),
            ])
            lost_opps = self.env['crm.lead'].with_context(active_test=False).search([
                ('user_id', '=', user.id), ('type', '=', 'opportunity'), ('active', '=', False),
                ('date_closed', '>=', ds), ('date_closed', '<=', de), ('probability', '=', 0),
            ])
            nb_won, nb_lost = len(won_opps), len(lost_opps)
            denom = nb_won + nb_lost
            taux  = round((nb_won / denom * 100) if denom else 0, 1)

            target_month = getattr(user, 'digest_target_invoicing_month', 0) or 10000.0
            inv_amount   = inv['amount'] if isinstance(inv, dict) else inv

            totals['ca']      += ca
            totals['invoiced'] += inv_amount
            totals['nb_won']   += nb_won
            totals['nb_opps']  += len(active_opps)

            rows.append({
                'name':         user.name,
                'ca':           fmt(ca),
                'invoiced':     fmt(inv_amount),
                'nb_invoices':  inv['count'] if isinstance(inv, dict) else 0,
                'nb_opps':      len(active_opps),
                'nb_won':       nb_won,
                'nb_lost':      nb_lost,
                'taux_transfo': taux,
                'target_month': fmt(target_month),
                'pct_target':   min(round(inv_amount / target_month * 100, 1) if target_month else 0, 100),
            })

        rows.sort(key=lambda r: r['ca'], reverse=True)

        return {
            'company':        company,
            'month_label':    report_month_start.strftime('%B %Y'),
            'generated_on':   today.strftime('%d/%m/%Y'),
            'rows':           rows,
            'total_ca':       fmt(totals['ca']),
            'total_invoiced': fmt(totals['invoiced']),
            'total_nb_won':   totals['nb_won'],
            'total_nb_opps':  totals['nb_opps'],
        }

    def action_send_monthly_report(self):
        """Génère et envoie le rapport mensuel consolidé à tous les managers + commerciaux."""
        self.ensure_one()

        template = self.env.ref(
            'sale_digest.email_template_monthly_report',
            raise_if_not_found=False,
        )
        if not template:
            raise UserError(_(
                "Template rapport mensuel introuvable : "
                "sale_digest.email_template_monthly_report"
            ))

        ctx = self._build_monthly_report_context()

        # Tous les utilisateurs internes actifs
        users = self.env['res.users'].search([
            ('share', '=', False),
            ('active', '=', True),
        ])

        # Managers commerciaux OU utilisateurs ayant activé le digest
        recipients = users.filtered(
            lambda u: (
                    u.has_group('sales_team.group_sale_manager')
                    or u.digest_enabled
            )
        )

        sent, errors = 0, []

        for user in recipients:
            try:
                template.with_context(**ctx).send_mail(
                    user.id,
                    force_send=True,
                    email_values={
                        'email_to': user.email,
                        'email_from': 'Nexconec <notifications@nexconec-europe.odoo.com>',
                        'subject': "📋 Rapport commercial mensuel — {}".format(
                            ctx['month_label']
                        ),
                        'auto_delete': False,
                    },
                )
                sent += 1

            except Exception as e:
                errors.append("{} : {}".format(user.name, str(e)))
                _logger.exception(
                    "Erreur rapport mensuel pour %s", user.name
                )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Rapport mensuel envoyé"),
                'message': _("{} email(s) envoyé(s).{}").format(
                    sent,
                    " {} erreur(s).".format(len(errors)) if errors else "",
                ),
                'type': 'warning' if errors else 'success',
                'sticky': bool(errors),
            },
        }

    @api.model
    def _cron_send_monthly_report(self):
        today  = date.today()
        digest = self.create({'date_start': today.replace(day=1), 'date_end': today})
        digest.action_send_monthly_report()
        _logger.info("Cron rapport mensuel terminé.")

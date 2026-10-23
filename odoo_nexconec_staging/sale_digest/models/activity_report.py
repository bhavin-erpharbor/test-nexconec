# -*- coding: utf-8 -*-
"""
activity_report.py
==================
Rapport d'activités hebdomadaire ciblé sur un commercial spécifique.

Fonctionnement :
  - On configure un ou plusieurs "commerciaux surveillés" + leurs destinataires
  - Chaque lundi, un email récapitulatif de la semaine précédente est envoyé
    aux destinataires configurés (pas au commercial lui-même)
  - Données : activités (appels/emails/tâches), RDV, devis, commandes confirmées
"""

import logging
from datetime import date, timedelta, datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ActivityReportConfig(models.Model):
    """
    Configuration d'un rapport d'activités pour un commercial donné.
    Chaque enregistrement = 1 commercial à surveiller + ses destinataires.
    """
    _name = 'sale.activity.report.config'
    _description = 'Configuration Rapport Activités Commercial'
    _order = 'watched_user_id'

    name = fields.Char(
        string='Nom du rapport',
        compute='_compute_name',
        store=True,
    )
    active = fields.Boolean(string='Actif', default=True)

    watched_user_id = fields.Many2one(
        'res.users',
        string='Commercial surveillé',
        required=True,
        domain=[('share', '=', False)],
        help="Commercial dont les activités seront rapportées chaque semaine.",
    )
    recipient_ids = fields.Many2many(
        'res.users',
        'activity_report_recipient_rel',
        'config_id', 'user_id',
        string='Destinataires',
        domain=[('share', '=', False)],
        required=True,
        help="Utilisateurs qui recevront ce rapport chaque lundi matin.",
    )

    @api.depends('watched_user_id')
    def _compute_name(self):
        for rec in self:
            rec.name = "Rapport activités — {}".format(
                rec.watched_user_id.name if rec.watched_user_id else "?"
            )


class ActivityReportSender(models.Model):
    """
    Modèle de traitement pour le calcul et l'envoi des rapports.
    Également utilisé comme entrée manuelle depuis l'interface.
    """
    _name = 'sale.activity.report'
    _description = 'Rapport Activités Hebdomadaire'
    _order = 'date_start desc'

    name = fields.Char(string='Référence', compute='_compute_name', store=True)
    date_start = fields.Date(
        string='Début de semaine',
        required=True,
        default=lambda self: date.today() - timedelta(days=7),
    )
    date_end = fields.Date(
        string='Fin de semaine',
        required=True,
        default=lambda self: date.today() - timedelta(days=1),
    )
    config_ids = fields.Many2many(
        'sale.activity.report.config',
        string='Configurations à envoyer',
        help="Laisser vide pour envoyer tous les rapports actifs.",
    )
    state = fields.Selection(
        [('draft', 'Brouillon'), ('sent', 'Envoyé'), ('error', 'Erreur')],
        string='État', default='draft',
    )
    sent_count = fields.Integer(string='Emails envoyés', readonly=True)
    error_log = fields.Text(string="Journal d'erreurs", readonly=True)

    @api.depends('date_start', 'date_end')
    def _compute_name(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                rec.name = "Rapport activités S{} — {} au {}".format(
                    rec.date_start.isocalendar()[1],
                    rec.date_start.strftime('%d/%m/%Y'),
                    rec.date_end.strftime('%d/%m/%Y'),
                )
            else:
                rec.name = "Rapport activités (brouillon)"

    # ─────────────────────────────────────────────────────────────
    # CALCUL DES KPIs
    # ─────────────────────────────────────────────────────────────

    def _get_ds_de(self):
        return (
            datetime.combine(self.date_start, datetime.min.time()),
            datetime.combine(self.date_end,   datetime.max.time()),
        )

    def _compute_activities_kpis(self, user):
        """
        Calcule toutes les activités réalisées sur la période pour un user.
        Retourne un dict avec le détail par type + les listes pour le template.
        """
        ds, de = self._get_ds_de()

        # ── Activités mail.activity (planifiées sur la période) ──
        activities = self.env['mail.activity'].search([
            ('user_id', '=', user.id),
            ('date_deadline', '>=', ds.date()),
            ('date_deadline', '<=', de.date()),
        ])

        calls  = activities.filtered(lambda a: a.activity_type_id.category == 'phonecall')
        emails = activities.filtered(lambda a: a.activity_type_id.category == 'email')
        others = activities.filtered(
            lambda a: a.activity_type_id.category not in ('phonecall', 'email')
        )

        # Activités en retard (toutes périodes)
        overdue = self.env['mail.activity'].search([
            ('user_id', '=', user.id),
            ('date_deadline', '<', date.today()),
        ])

        # ── RDV Agenda ──
        meetings = self.env['calendar.event'].search([
            ('user_id', '=', user.id),
            ('start', '>=', ds),
            ('start', '<=', de),
            ('active', '=', True),
        ])

        # ── Devis émis ──
        quotes = self.env['sale.order'].search([
            ('user_id', '=', user.id),
            ('state', 'in', ['draft', 'sent']),
            ('create_date', '>=', ds),
            ('create_date', '<=', de),
        ])

        # ── Commandes confirmées ──
        orders = self.env['sale.order'].search([
            ('user_id', '=', user.id),
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', ds),
            ('date_order', '<=', de),
        ])

        return {
            # Activités
            'nb_calls':    len(calls),
            'nb_emails':   len(emails),
            'nb_others':   len(others),
            'nb_overdue':  len(overdue),
            'activities_list': activities[:20],  # Top 20 pour le tableau

            # RDV
            'nb_meetings': len(meetings),
            'meetings_list': meetings[:10],

            # Devis
            'nb_quotes':      len(quotes),
            'quotes_amount':  sum(quotes.mapped('amount_untaxed')),
            'quotes_list':    quotes[:10],

            # Commandes
            'nb_orders':      len(orders),
            'orders_amount':  sum(orders.mapped('amount_untaxed')),
            'orders_list':    orders[:10],
        }

    def _build_report_context(self, config):
        """Construit le contexte template pour une config donnée."""
        user    = config.watched_user_id
        company = user.company_id or self.env.company
        currency = company.currency_id
        kpis    = self._compute_activities_kpis(user)

        def fmt(amount):
            if not amount:
                return "0 {}".format(currency.symbol)
            return "{:,.0f} {}".format(amount, currency.symbol).replace(',', ' ')

        return {
            'company':        company,
            'watched_user':   user,
            'date_start':     self.date_start,
            'date_end':       self.date_end,
            'week_label':     "S{} — {} au {}".format(
                self.date_start.isocalendar()[1],
                self.date_start.strftime('%d/%m/%Y'),
                self.date_end.strftime('%d/%m/%Y'),
            ),
            'base_url': self.env['ir.config_parameter'].sudo().get_param('web.base.url'),

            # KPIs résumés
            'nb_calls':    kpis['nb_calls'],
            'nb_emails':   kpis['nb_emails'],
            'nb_others':   kpis['nb_others'],
            'nb_overdue':  kpis['nb_overdue'],
            'nb_meetings': kpis['nb_meetings'],
            'nb_quotes':   kpis['nb_quotes'],
            'nb_orders':   kpis['nb_orders'],

            # Montants formatés
            'quotes_amount': fmt(kpis['quotes_amount']),
            'orders_amount': fmt(kpis['orders_amount']),

            # Listes pour les tableaux détaillés
            'activities_list': kpis['activities_list'],
            'meetings_list':   kpis['meetings_list'],
            'quotes_list':     kpis['quotes_list'],
            'orders_list':     kpis['orders_list'],
        }

    # ─────────────────────────────────────────────────────────────
    # ENVOI
    # ─────────────────────────────────────────────────────────────

    def _get_configs(self):
        if self.config_ids:
            return self.config_ids
        return self.env['sale.activity.report.config'].search([('active', '=', True)])

    def action_send_reports(self):
        self.ensure_one()
        template = self.env.ref(
            'sale_digest.email_template_activity_report',
            raise_if_not_found=False,
        )
        if not template:
            raise UserError(_("Template introuvable : sale_digest.email_template_activity_report"))

        configs = self._get_configs()
        sent, errors = 0, []

        for config in configs:
            try:
                ctx = self._build_report_context(config)
                for recipient in config.recipient_ids:
                    template.with_context(**ctx).send_mail(
                        recipient.id,
                        force_send=True,
                        email_values={
                            'email_to': recipient.email,
                            'subject': "📋 Activités de {} — {}".format(
                                config.watched_user_id.name,
                                ctx['week_label'],
                            ),
                            'auto_delete': False,
                        },
                    )
                    sent += 1
                    _logger.info(
                        "Rapport activités %s → %s envoyé",
                        config.watched_user_id.name, recipient.email,
                    )
            except Exception as e:
                errors.append("{} : {}".format(config.name, str(e)))
                _logger.error("Erreur rapport activités %s : %s", config.name, e, exc_info=True)

        self.write({
            'state':      'error' if errors else 'sent',
            'sent_count': sent,
            'error_log':  "\n".join(errors) if errors else False,
        })
        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'title':   _("Rapports envoyés"),
                'message': _("{} email(s) envoyé(s).{}").format(
                    sent, " {} erreur(s).".format(len(errors)) if errors else ""),
                'type':    'warning' if errors else 'success',
                'sticky':  bool(errors),
            },
        }

    # ─────────────────────────────────────────────────────────────
    # CRON
    # ─────────────────────────────────────────────────────────────

    @api.model
    def _cron_send_activity_reports(self):
        today        = date.today()
        last_monday  = today - timedelta(days=today.weekday() + 7)
        last_sunday  = last_monday + timedelta(days=6)
        report = self.create({'date_start': last_monday, 'date_end': last_sunday})
        report.action_send_reports()
        _logger.info(
            "Cron rapports activités terminé : %s email(s) envoyé(s).",
            report.sent_count,
        )

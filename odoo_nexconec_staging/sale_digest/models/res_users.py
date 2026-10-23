# -*- coding: utf-8 -*-
"""
res_users.py
============
Extension du modèle res.users pour ajouter :
  - L'activation/désactivation du digest par commercial
  - Les objectifs de facturation mensuels et annuels personnalisés
"""

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    # ── Activation du digest ──────────────────────────────────────
    digest_enabled = fields.Boolean(
        string='Recevoir le digest commercial',
        default=True,
        help="Si coché, ce commercial recevra le digest email chaque lundi matin.",
    )

    # ── Objectifs de facturation personnalisés ────────────────────
    digest_target_invoicing_month = fields.Float(
        string='Objectif facturation mensuel (€)',
        default=10000.0,
        help="Objectif de facturation mensuel pour ce commercial.",
    )
    digest_target_invoicing_year = fields.Float(
        string='Objectif facturation annuel (€)',
        default=100000.0,
        help="Objectif de facturation annuel pour ce commercial.",
    )
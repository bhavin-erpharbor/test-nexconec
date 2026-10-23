# 📊 Module `sale_digest` — Digest Commercial Hebdomadaire Odoo

## Vue d'ensemble

Ce module envoie automatiquement chaque lundi matin un email personnalisé à chaque
commercial avec un récap de sa semaine : CA, opportunités, activités, facturation et
avancement des objectifs mensuels.

---

## Structure du module

```
sale_digest/
├── __manifest__.py               # Déclaration du module
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── sale_digest.py            # ★ Logique principale — calcul des KPIs + envoi
│   └── res_users.py              # Extension utilisateur (objectifs, activation)
├── views/
│   ├── sale_digest_views.xml     # Interface de gestion des digests
│   └── res_users_views.xml       # Onglet objectifs dans la fiche utilisateur
├── data/
│   ├── mail_template_digest.xml  # Template email QWeb (HTML)
│   └── ir_cron_digest.xml        # Cron lundi 07h00
├── security/
│   └── ir.model.access.csv       # Droits d'accès
└── README.md
```

---

## Installation

### 1. Copier le module

```bash
cp -r sale_digest /path/to/odoo/addons/
# ou dans votre dossier custom-addons déclaré dans odoo.conf
```

### 2. Redémarrer Odoo et mettre à jour la liste des apps

```bash
./odoo-bin -c odoo.conf -u sale_digest -d votre_base
# ou via interface : Paramètres > Activer le mode développeur > Apps > Mettre à jour
```

### 3. Installer le module

Apps > Rechercher "Digest Commercial" > Installer

### Dépendances requises

| Module Odoo | Usage |
|-------------|-------|
| `sale_crm`  | Commandes de vente + opportunités CRM |
| `account`   | Facturation |
| `mail`      | Envoi d'emails |
| `calendar`  | Comptage des RDV |
| `project`   | Comptage des tâches (optionnel) |

---

## Configuration

### Activer le digest pour un commercial

1. Paramètres > Utilisateurs > [fiche du commercial]
2. Onglet **"🎯 Objectifs Digest"**
3. Cocher **"Recevoir le digest commercial hebdomadaire"**
4. Renseigner les objectifs mensuels personnalisés

### Vérifier le cron

Paramètres > Technique > Automatisation > Actions planifiées
→ Chercher **"Digest Commercial — Envoi hebdomadaire"**
→ Vérifier que la prochaine exécution est bien un lundi à 07:00

### Envoyer un digest de test

Ventes > Digests Commerciaux > Nouveau
- Choisir une période
- Sélectionner un ou plusieurs commerciaux (destinataires)
- Cliquer **"🚀 Envoyer le digest maintenant"**

---

## Comment ça marche — flux de données

```
ir.cron (lundi 07h00)
    └── SaleDigest._cron_send_weekly_digest()
            └── Crée un enregistrement sale.digest (lun–dim S-1)
            └── action_send_digest()
                    └── Pour chaque res.users eligible :
                            └── _build_template_context(user)
                                    ├── _compute_ca()              → sale.order
                                    ├── _compute_opportunities()   → crm.lead
                                    ├── _compute_activities()      → mail.activity + calendar.event
                                    ├── _compute_invoicing()       → account.move
                                    └── _compute_monthly_objectives() → agrégation mois en cours
                            └── template.send_mail(user.id)        → mail.mail
```

---

## Personnalisation

### Ajouter un KPI

1. Ajouter une méthode `_compute_mon_kpi(self, user)` dans `sale_digest.py`
2. L'appeler dans `_build_template_context()` et ajouter la clé au dict retourné
3. Référencer `ctx.get('mon_kpi')` dans `mail_template_digest.xml`

### Changer la fréquence d'envoi

Dans `data/ir_cron_digest.xml` :
```xml
<field name="interval_number">1</field>
<field name="interval_type">weeks</field>  <!-- days / weeks / months -->
```

### Changer l'heure d'envoi

Modifier `nextcall` dans le cron XML, ou depuis l'interface Odoo.

### Cibler certaines équipes commerciales

Modifier `_get_target_users()` dans `sale_digest.py` :

```python
def _get_target_users(self):
    if self.user_ids:
        return self.user_ids
    # Exemple : seulement l'équipe "Grands Comptes"
    team = self.env['crm.team'].search([('name', '=', 'Grands Comptes')], limit=1)
    if team:
        return team.member_ids.filtered(lambda u: u.digest_enabled)
    return self.env['res.users'].search([
        ('share', '=', False),
        ('active', '=', True),
        ('digest_enabled', '=', True),
    ])
```

---

## Dépannage

| Problème | Solution |
|----------|----------|
| Emails non reçus | Vérifier la config serveur SMTP : Paramètres > Technique > Email > Serveurs sortants |
| KPIs à 0 | Activer le mode debug et appeler `action_send_digest()` manuellement sur une période connue |
| Erreur `Template introuvable` | Vérifier que `sale_digest.email_template_digest` existe dans Paramètres > Technique > Email > Templates |
| `mail.activity.done` introuvable | Normal si vous n'avez pas le module `mail_activity_done` — le bloc est protégé par un `if` |
| Cron ne tourne pas | Vérifier que le worker Odoo est actif (pas de mode `--workers 0`) |

---

## Compatibilité

- Odoo **17.0** (Community & Enterprise)
- Python 3.10+
- Pour Odoo 16 : remplacer `t-attf-class` par `t-att-class` si nécessaire

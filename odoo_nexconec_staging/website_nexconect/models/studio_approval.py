
from ast import literal_eval

from odoo import api, models, fields, _
from odoo.osv import expression
from odoo.exceptions import ValidationError, AccessError, UserError


class StudioApprovalRule(models.Model):
    _inherit = "studio.approval.rule"
    _description = "Studio Approval Rule"

    @api.model
    def check_approval(self, model, res_id, method, action_id):
        """Check if the current user can proceed with an action.

        Check existing rules for the requested action and provided record; during this
        check, any rule which the user can approve will be approved automatically.

        Returns a dict indicating whether the action can proceed (`approved` key)
        (when *all* applicable rules have an entry that mark approval), as well as the
        rules and entries that are part of the approval flow for the specified action.

        :param str model: technical name of the model on which the action takes place
        :param int res_id: database ID of the record for which the action must be approved
        :param str method: method of the action that the user wants to run
        :param int action_id: database ID of the ir.actions.action that the user wants to run
        :return: a dict describing the result of the approval flow
        :rtype dict:
        :raise: UserError if action_id and method are both truthy (rules can only apply to a method
                or an action, not both)
        :raise: AccessError if the user does not have write access to the underlying record
        """
        
        self = self._clean_context()
        if method and action_id:
            raise UserError(_('Approvals can only be done on a method or an action, not both.'))
        record = self.env[model].browse(res_id)
        # we check that the user has write access on the underlying record before doing anything
        # if another type of access is necessary to perform the action, it will be checked
        # there anyway
        record.check_access('write')
        ruleSudo = self.sudo()
        domain = self._get_rule_domain(model, method, action_id)
        # order by 'exclusive_user' so that restrictive rules are approved first
        rules_data = ruleSudo.search_read(
            domain=domain,
            fields=['message', 'name', 'domain'],
            order='exclusive_user desc, id asc'
        )
        applicable_rule_ids = list()
        for rule in rules_data:
            rule_domain = rule.get('domain') and literal_eval(rule['domain'])
            if not rule_domain or record.filtered_domain(rule_domain):
                # the record matches the domain of the rule
                # or the rule has no domain set on it
                applicable_rule_ids.append(rule['id'])
        rules_data = list(filter(lambda r: r['id'] in applicable_rule_ids, rules_data))
        if method == 'action_confirm' and model == 'sale.order' and res_id:
            sale_order = self.env[model].sudo().browse(res_id)
            if sale_order.x_studio_amount_due <= sale_order.x_studio_credit_limit:
                rules_data = []
        if not rules_data:
            # no rule matching our operation: return early, the user can proceed
            return {'approved': True, 'rules': [], 'entries': []}
        # need sudo, we need to check entries from other people and through record rules
        # users can only see their own entries by default
        entries_data = self.env['studio.approval.entry'].sudo().search_read(
            domain=[('model', '=', model), ('res_id', '=', res_id), ('rule_id', 'in', applicable_rule_ids)],
            fields=['approved', 'rule_id', 'user_id'])
        entries_by_rule = dict.fromkeys(applicable_rule_ids, False)
        for rule_id in entries_by_rule:
            candidate_entry = list(filter(lambda e: e['rule_id'][0] == rule_id, entries_data))
            candidate_entry = candidate_entry and candidate_entry[0]
            if not candidate_entry:
                # there is a rule that has no entry yet, try to approve it
                try:
                    new_entry = self.browse(rule_id)._set_approval(res_id, True)
                    entries_data.append({
                        'id': new_entry.id,
                        'approved': True,
                        'rule_id': [rule_id, False],
                        'user_id': (self.env.user.id, self.env.user.display_name),
                    })
                    entries_by_rule[rule_id] = True
                except UserError:
                    # either the user doesn't have the required group, or they already
                    # validated another rule for a 'exclusive_user' approval
                    # nothing to do here
                    pass
            else:
                entries_by_rule[rule_id] = candidate_entry['approved']
        return {
            'approved': all(entries_by_rule.values()),
            'rules': rules_data,
            'entries': entries_data,
        }

# -*- coding: utf-8 -*-
"""
Diya CRM — Lead Assignment Rules
Frontend se company-wise Fixed ya Round Robin assignment configure karo.
"""
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class DiyaCrmAssignmentRule(models.Model):
    _name = "diyacrm.assignment.rule"
    _description = "Diya CRM Lead Assignment Rule"
    _order = "sequence asc, id asc"
    _rec_name = "company_id"

    # ── Core Fields ──────────────────────────────────────────────────────────
    sequence = fields.Integer(
        string="Priority",
        default=10,
        help="Chota number = zyada priority (pehle match hoga)"
    )
    active = fields.Boolean(default=True, string="Active")
    company_id = fields.Many2one(
        "res.company",
        string="Company / Project",
        required=True,
        ondelete="cascade",
        index=True,
    )

    # ── Assignment Type ───────────────────────────────────────────────────────
    assignment_type = fields.Selection([
        ("fixed",       "Fixed — Hamesha ek hi person ko"),
        ("round_robin", "Round Robin — Baari baari distribute karo"),
    ], string="Assignment Type", required=True, default="fixed")

    # ── Fixed Assignment ──────────────────────────────────────────────────────
    fixed_user_id = fields.Many2one(
        "res.users",
        string="Assign To (Fixed)",
        domain=[("share", "=", False)],
        help="Yeh company ke har naye lead ko is salesperson ko assign hoga.",
    )

    # ── Round Robin ───────────────────────────────────────────────────────────
    round_robin_user_ids = fields.Many2many(
        "res.users",
        "diyacrm_assignment_rule_user_rel",
        "rule_id",
        "user_id",
        string="Round Robin Salespersons",
        domain=[("share", "=", False)],
        help="Leads ko inke beech baari baari distribute kiya jayega.",
    )
    last_assigned_user_id = fields.Many2one(
        "res.users",
        string="Last Assigned To",
        readonly=True,
        help="Round Robin ke liye — pichli baar kisko mila tha (auto-managed)"
    )

    # ── Source Triggers ───────────────────────────────────────────────────────
    apply_on_whatsapp = fields.Boolean(
        string="WhatsApp Leads pe Apply karo",
        default=True,
        help="WhatsApp se aane wale naye leads par yeh rule lagao"
    )
    apply_on_manual = fields.Boolean(
        string="Manual Leads pe Apply karo",
        default=True,
        help="CRM me manually create hone wale leads par yeh rule lagao"
    )
    apply_on_dialer = fields.Boolean(
        string="Dialer Leads pe Apply karo",
        default=True,
        help="Dialer call se bane leads par yeh rule lagao"
    )

    # ── Stats (computed) ──────────────────────────────────────────────────────
    lead_count = fields.Integer(
        string="Leads Assigned",
        compute="_compute_lead_count",
    )

    def _compute_lead_count(self):
        for rule in self:
            rule.lead_count = self.env["crm.lead"].search_count([
                ("company_id", "=", rule.company_id.id),
            ])

    # ── Constraints ───────────────────────────────────────────────────────────
    _sql_constraints = [
        ("unique_company_rule", "UNIQUE(company_id)",
         "Ek company ke liye sirf ek hi assignment rule ho sakta hai!")
    ]

    @api.constrains("assignment_type", "fixed_user_id", "round_robin_user_ids")
    def _check_assignment_config(self):
        for rule in self:
            if rule.assignment_type == "fixed" and not rule.fixed_user_id:
                raise ValidationError(
                    _("Fixed assignment ke liye 'Assign To' salesperson select karna zaroori hai!")
                )
            if rule.assignment_type == "round_robin" and not rule.round_robin_user_ids:
                raise ValidationError(
                    _("Round Robin ke liye kam se kam 1 salesperson select karna zaroori hai!")
                )

    # ── Core Method: Get Next Assigned User ───────────────────────────────────
    def get_next_user(self):
        """
        Rule ke hisaab se agla salesperson return karo.
        Fixed: hamesha fixed_user_id
        Round Robin: last assigned ke baad wala (circular)
        """
        self.ensure_one()
        if not self.active:
            return False

        if self.assignment_type == "fixed":
            return self.fixed_user_id or False

        elif self.assignment_type == "round_robin":
            users = self.round_robin_user_ids
            if not users:
                return False
            if len(users) == 1:
                return users[0]

            # Find next user after last_assigned_user_id
            user_ids = users.ids
            if not self.last_assigned_user_id or self.last_assigned_user_id.id not in user_ids:
                next_user = users[0]
            else:
                current_idx = user_ids.index(self.last_assigned_user_id.id)
                next_idx = (current_idx + 1) % len(user_ids)
                next_user = users.browse(user_ids[next_idx])

            # Save last assigned (use sudo to avoid access issues)
            self.sudo().write({"last_assigned_user_id": next_user.id})
            _logger.info(
                "Round Robin [%s]: Next assigned → %s",
                self.company_id.name, next_user.name
            )
            return next_user

        return False

    # ── Class Method: Find Rule for a Company ─────────────────────────────────
    @api.model
    def get_rule_for_company(self, company):
        """
        Company ke liye active rule dhundo.
        Returns: rule recordset (can be empty)
        """
        if not company:
            return self.browse()
        return self.search([
            ("company_id", "=", company.id),
            ("active", "=", True),
        ], limit=1)

    @api.model
    def get_assigned_user_for_company(self, company, source="manual"):
        """
        Company + source ke liye next assigned user return karo.
        source: 'whatsapp', 'manual', 'dialer'
        Returns: res.users record or False
        """
        rule = self.get_rule_for_company(company)
        if not rule:
            return False

        # Check if rule applies to this source
        if source == "whatsapp" and not rule.apply_on_whatsapp:
            return False
        if source == "manual" and not rule.apply_on_manual:
            return False
        if source == "dialer" and not rule.apply_on_dialer:
            return False

        return rule.get_next_user()

    # ── Button: Reset Round Robin ─────────────────────────────────────────────
    def action_reset_round_robin(self):
        """Round Robin ko reset karo (pehle wale se start hoga)"""
        self.ensure_one()
        self.sudo().write({"last_assigned_user_id": False})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Round Robin Reset!",
                "message": f"{self.company_id.name} ke liye Round Robin reset ho gaya. Ab pehle person se start hoga.",
                "type": "success",
                "sticky": False,
            },
        }

    # ── Button: View Leads ────────────────────────────────────────────────────
    def action_view_leads(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"{self.company_id.name} — Leads",
            "res_model": "crm.lead",
            "view_mode": "list,form",
            "domain": [("company_id", "=", self.company_id.id)],
            "context": {"default_company_id": self.company_id.id},
        }

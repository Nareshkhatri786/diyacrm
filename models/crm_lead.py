import logging
from markupsafe import Markup
_logger = logging.getLogger(__name__)
# -*- coding: utf-8 -*-
import datetime
import pytz
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError


def normalize_lead_phone(raw_phone):
    """
    Clean and normalize phone number:
    - Strips non-digits
    - For Indian numbers (10 digits, 11 starting with 0, or 12 starting with 91):
      returns clean 10-digit number (e.g. '9227777314')
    - For international numbers: returns '+<digits>'
    """
    if not raw_phone:
        return False
    digits = re.sub(r'\D', '', str(raw_phone))
    if not digits:
        return False
    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        return digits[2:]
    elif len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
        return digits[1:]
    elif len(digits) == 10 and digits[0] in "6789":
        return digits
    elif len(digits) > 10 and digits.startswith("91"):
        return digits[-10:]
    elif len(digits) >= 10:
        return digits[-10:] if not str(raw_phone).strip().startswith('+') else f"+{digits}"
    return digits


class CrmLead(models.Model):
    _inherit = "crm.lead"

    area = fields.Selection([
        ("hanspura", "Hanspura"), ("nikol", "Nikol"), ("vatva_lambha", "Vatva / Lambha"),
        ("naroda_nava_naroda", "Naroda / Nava Naroda"), ("vastral", "Vastral"), ("odhav", "Odhav"),
        ("narol", "Narol"), ("isanpur", "Isanpur"), ("ghodasar", "Ghodasar"),
        ("kathwada", "Kathwada"), ("hathijan", "Hathijan"), ("ctm_ramol", "CTM / Ramol"),
        ("aslali", "Aslali"), ("maninagar", "Maninagar"), ("other_ahmedabad", "Other Area (Ahmedabad)"),
        ("outside_ahmedabad", "Outside Ahmedabad")
    ], string="Area", tracking=True)

    unit_type = fields.Selection([
        ("2bhk", "2 BHK"), ("3bhk", "3 BHK"), ("4bhk", "4 BHK"), ("shop", "Shop")
    ], string="Unit Type", tracking=True)

    property_unit_id = fields.Many2one("crm.property.unit", string="Booked / Selected Unit", tracking=True)
    unit_block = fields.Selection(related="property_unit_id.block", string="Unit Block", readonly=True)
    unit_floor = fields.Selection(related="property_unit_id.floor", string="Unit Floor", readonly=True)
    unit_size = fields.Selection(related="property_unit_id.size_sq_yard", string="Unit Size", readonly=True)
    unit_facing = fields.Selection(related="property_unit_id.facing", string="Unit Facing", readonly=True)
    unit_plc = fields.Boolean(related="property_unit_id.location_charge", string="Unit PLC", readonly=True)

    lead_temperature = fields.Selection([
        ("hot", "Hot"), ("warm", "Warm"), ("cold", "Cold")
    ], string="Status", default="warm", tracking=True)

    last_call_outcome = fields.Selection([
        ("answered", "Answered"), ("no_answer", "No answer"),
        ("busy", "Busy"), ("switched_off", "Switched off")
    ], string="Last Call Outcome", tracking=True)

    last_call_whatsapp_date = fields.Datetime("Last Call WhatsApp Sent", readonly=True)
    last_call_whatsapp_type = fields.Selection([
        ("answered", "Connected"),
        ("no_answer", "Missed / Busy")
    ], string="Last Call WhatsApp Type", readonly=True)

    whatsapp_message_ids = fields.One2many("crm.lead.whatsapp.message", "lead_id", string="WhatsApp Messages")
    whatsapp_message_count = fields.Integer("WhatsApp Messages Count", compute="_compute_whatsapp_message_count")

    @api.depends("whatsapp_message_ids")
    def _compute_whatsapp_message_count(self):
        for lead in self:
            lead.whatsapp_message_count = len(lead.whatsapp_message_ids)

    finance_mode = fields.Selection([
        ("loan", "Loan"), ("cash", "Self-Funding / Cash"), ("both", "Loan + Cash")
    ], string="Finance Mode", tracking=True)

    purchase_timeline = fields.Selection([
        ("immediate", "< 30 Days (Immediate)"), ("1_3_months", "1 - 3 Months"),
        ("3_6_months", "3 - 6 Months"), ("more_6_months", "> 6 Months")
    ], string="Purchase Timeline", tracking=True)

    budget_fit = fields.Selection([
        ("within", "Within Budget"), ("slightly_high", "Slightly Stretchable"), ("over_budget", "Over Budget")
    ], string="Budget Fit", tracking=True)

    decision_maker_present = fields.Selection([
        ("yes", "With Family / Spouse (Decision Maker Present)"),
        ("no", "Individual Only (Need Follow-up with Family)")
    ], string="Decision Maker Accompanying", tracking=True)

    @staticmethod
    def _default_unit_type_for_company(company_name):
        if not company_name:
            return False
        name = str(company_name).lower()
        if "devi" in name:
            return "4bhk"
        if any(kw in name for kw in ["shreemad", "royal", "1st", "first"]):
            return "3bhk"
        return False

    @api.onchange("company_id")
    def _onchange_company_unit_type(self):
        if self.company_id:
            default_ut = self._default_unit_type_for_company(self.company_id.name)
            if default_ut:
                self.unit_type = default_ut

    @api.depends("activity_ids.activity_type_id")
    def _compute_meeting_display(self):
        super()._compute_meeting_display()
        for lead in self:
            if lead.meeting_display_label == "No Meeting":
                lead.meeting_display_label = "No Site Visit"
            elif lead.meeting_display_label == "Next Meeting":
                lead.meeting_display_label = "Next Site Visit"
            elif lead.meeting_display_label == "Last Meeting":
                lead.meeting_display_label = "Last Site Visit"

    @api.model
    def find_lead_by_phone(self, phone, company_id=None, exclude_id=None, active_test=True):
        """
        Robust phone lookup across lead records:
        - Extracts digits and matches on the last 10 digits (ignoring spaces, dashes, +91, 0 prefix, etc.)
        - Scoped strictly by company_id if provided (multi-company support: same phone allowed in different companies)
        - Supports active_test=False to find lost/archived leads (for reactivation)
        """
        if not phone:
            return self.env["crm.lead"]
        digits = re.sub(r'\D', '', str(phone))
        if not digits:
            return self.env["crm.lead"]

        phone_10 = digits[-10:] if len(digits) >= 10 else digits
        where_clauses = ["type = 'opportunity'"]
        params = []

        if len(digits) >= 10:
            where_clauses.append("RIGHT(regexp_replace(COALESCE(phone, ''), '\\D', '', 'g'), 10) = %s")
            params.append(phone_10)
        else:
            where_clauses.append("regexp_replace(COALESCE(phone, ''), '\\D', '', 'g') = %s")
            params.append(digits)

        if company_id:
            c_id = company_id.id if hasattr(company_id, 'id') else int(company_id)
            where_clauses.append("company_id = %s")
            params.append(c_id)

        if exclude_id:
            e_id = exclude_id.id if hasattr(exclude_id, 'id') else int(exclude_id)
            where_clauses.append("id != %s")
            params.append(e_id)

        if active_test:
            where_clauses.append("active = true")

        query = f"""
            SELECT id FROM crm_lead
            WHERE {" AND ".join(where_clauses)}
            ORDER BY active DESC, write_date DESC, id DESC
            LIMIT 1
        """
        self._cr.execute(query, tuple(params))
        res = self._cr.fetchone()
        if res:
            return self.browse(res[0])
        return self.env["crm.lead"]

    def _find_duplicate_phone(self, phone, company_id, exclude_id=None):
        return self.find_lead_by_phone(phone, company_id=company_id, exclude_id=exclude_id, active_test=True)

    @api.onchange("phone")
    def _onchange_phone_duplicate_check(self):
        if not self.phone:
            return
        company_id = self.company_id.id if self.company_id else self.env.company.id
        existing = self.find_lead_by_phone(self.phone, company_id=company_id, exclude_id=self._origin.id, active_test=True)
        if existing:
            base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
            opp_url = base_url + "/odoo/crm/" + str(existing.id)
            return {
                "warning": {
                    "title": _("Duplicate Phone Number"),
                    "message": "This phone number (%s) already exists in your company!\n\nOpportunity : %s\nSalesperson : %s\nStage : %s\nCompany : %s\n\nDirect Link : %s" % (
                        self.phone, existing.name or "-", existing.user_id.name or "Unassigned",
                        existing.stage_id.name or "-", existing.company_id.name or "-", opp_url
                    )
                }
            }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("type", "opportunity") != "opportunity":
                continue
            if not vals.get("unit_type"):
                company_id = vals.get("company_id") or self.env.company.id
                company = self.env["res.company"].browse(company_id)
                default_ut = self._default_unit_type_for_company(company.name)
                if default_ut:
                    vals["unit_type"] = default_ut
            phone = vals.get("phone")
            if phone:
                normalized = normalize_lead_phone(phone)
                if normalized:
                    vals["phone"] = normalized
                company_id = vals.get("company_id") or self.env.company.id
                existing = self.find_lead_by_phone(vals["phone"], company_id=company_id, active_test=True)
                if existing:
                    base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
                    opp_url = base_url + "/odoo/crm/" + str(existing.id)
                    raise UserError(_("Duplicate Phone Number Detected!\n\nThis phone number (%s) already exists in your company!\n\nOpportunity : %s\nSalesperson : %s\nStage : %s\nCompany : %s\n\nDirect Link : %s") % (
                        vals["phone"], existing.name or "-", existing.user_id.name or "Unassigned",
                        existing.stage_id.name or "-", existing.company_id.name or "-", opp_url
                    ))
        return super().create(vals_list)

    def write(self, vals):
        if "phone" in vals and vals.get("phone"):
            normalized = normalize_lead_phone(vals["phone"])
            if normalized:
                vals["phone"] = normalized
            for record in self:
                company_id = vals.get("company_id") or record.company_id.id
                existing = self.find_lead_by_phone(vals["phone"], company_id=company_id, exclude_id=record.id, active_test=True)
                if existing:
                    base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
                    opp_url = base_url + "/odoo/crm/" + str(existing.id)
                    raise UserError(_("Duplicate Phone Number Detected!\n\nThis phone number (%s) already exists in your company!\n\nOpportunity : %s\nSalesperson : %s\nStage : %s\nCompany : %s\n\nDirect Link : %s") % (
                        vals["phone"], existing.name or "-", existing.user_id.name or "Unassigned",
                        existing.stage_id.name or "-", existing.company_id.name or "-", opp_url
                    ))
        return super().write(vals)

    def web_save(self, vals, specification):
        if not self:
            self = self.create(vals)
        else:
            self.write(vals)
        try:
            return self.web_read(specification)
        except Exception:
            return self.sudo().web_read(specification)

    def action_open_whatsapp_wizard(self):
        self.ensure_one()
        if not self.phone:
            raise UserError(_("Please specify a phone number on the lead first."))
        return {
            "name": _("Send WhatsApp Message"),
            "type": "ir.actions.act_window",
            "res_model": "crm.whatsapp.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_lead_id": self.id, "default_phone": self.phone}
        }

    @api.model
    def get_dashboard_data(self, period="48h", company_id="all", user_id="all"):
        user_tz = pytz.timezone(self.env.user.tz or "Asia/Kolkata")
        now_dt = datetime.datetime.now(user_tz)
        if period == "today":
            start_dt = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = now_dt
        elif period == "yesterday":
            yesterday = now_dt - datetime.timedelta(days=1)
            start_dt = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == "week":
            start_dt = (now_dt - datetime.timedelta(days=now_dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = now_dt
        elif period == "month":
            start_dt = now_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_dt = now_dt
        elif period == "48h":
            start_dt = now_dt - datetime.timedelta(hours=48)
            end_dt = now_dt
        else:
            start_dt = now_dt - datetime.timedelta(days=365)
            end_dt = now_dt

        start_utc = start_dt.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
        end_utc = end_dt.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")

        allowed_companies = self.env.companies
        if company_id != "all" and company_id:
            try:
                target_cid = int(company_id)
                target_comp = allowed_companies.filtered(lambda c: c.id == target_cid)
                active_companies = target_comp if target_comp else self.env["res.company"].browse([target_cid])
            except Exception:
                active_companies = allowed_companies
        else:
            active_companies = allowed_companies

        company_ids = active_companies.ids
        base_domain = [("company_id", "in", company_ids)]
        if user_id != "all" and user_id:
            try:
                base_domain.append(("user_id", "=", int(user_id)))
            except Exception:
                pass

        all_scoped_leads = self.with_context(active_test=False).search(base_domain)
        lead_ids = all_scoped_leads.ids

        # Period leads (for New Opportunities metric)
        period_leads = all_scoped_leads.filtered(
            lambda l: l.create_date and fields.Datetime.to_string(l.create_date) >= start_utc and fields.Datetime.to_string(l.create_date) <= end_utc
        )

        # 1. Calling Analytics from mail.message
        msg_domain = [
            ("model", "=", "crm.lead"),
            ("date", ">=", start_utc),
            ("date", "<=", end_utc),
            "|", "|", "|",
            ("body", "ilike", "%Call%"),
            ("body", "ilike", "%Dialer%"),
            ("body", "ilike", "%Answered%"),
            ("body", "ilike", "%Outgoing%")
        ]
        if lead_ids:
            msg_domain.append(("res_id", "in", lead_ids))
        elif company_id != "all" or user_id != "all":
            msg_domain.append(("res_id", "in", [-1]))

        call_msgs = self.env["mail.message"].search(msg_domain)

        out_answered = 0
        out_noanswer = 0
        out_busy = 0
        out_switched = 0
        user_partner_map = {u.partner_id.id: u.id for u in self.env["res.users"].search([("share", "=", False)])}
        user_call_counts = {}

        for m in call_msgs:
            b = (m.body or "").lower()
            if "no answer" in b or "not answered" in b or "unanswered" in b:
                out_noanswer += 1
            elif "busy" in b or "block" in b:
                out_busy += 1
            elif "switched" in b or "switch off" in b or "miss" in b or "reject" in b or "not reachable" in b:
                out_switched += 1
            else:
                out_answered += 1

            uid = user_partner_map.get(m.author_id.id)
            if uid:
                user_call_counts[uid] = user_call_counts.get(uid, 0) + 1

        total_calls = len(call_msgs)

        def calc_pct(val, tot):
            return int(round((val / tot) * 100)) if tot > 0 else 0

        connected_pct = calc_pct(out_answered, total_calls)

        # 2. Site Visits & Opportunities
        visit_done_leads = all_scoped_leads.filtered(
            lambda l: l.active and any(w in (l.stage_id.name or "").lower() for w in ["visit done", "done"])
        )
        visits_done = len(visit_done_leads)

        site_acts = self.env["mail.activity"].search([
            ("res_model", "=", "crm.lead"), ("res_id", "in", lead_ids),
            ("activity_type_id.name", "ilike", "site"),
            ("create_date", ">=", start_utc), ("create_date", "<=", end_utc)
        ])
        visits_scheduled = max(
            len(site_acts),
            len(all_scoped_leads.filtered(lambda l: l.active and "scheduled" in (l.stage_id.name or "").lower()))
        )

        won_leads = all_scoped_leads.filtered(
            lambda l: l.active and (l.probability == 100 or "won" in (l.stage_id.name or "").lower())
        )
        won_count = len(won_leads)
        new_opps_count = len(period_leads)
        updated_opps_count = len(set(call_msgs.mapped("res_id")) | set(period_leads.ids))

        # 3. Stages Funnel
        all_stages = self.env["crm.stage"].search([], order="sequence asc")
        stages_data = []
        for stage in all_stages:
            stg_count = len(all_scoped_leads.filtered(lambda l: l.active and l.stage_id.id == stage.id))
            stages_data.append({"id": stage.id, "name": stage.name, "sequence": stage.sequence, "count": stg_count})

        # 4. Temperature
        temp_data = {
            "hot": len(all_scoped_leads.filtered(lambda l: l.active and l.lead_temperature == "hot")),
            "warm": len(all_scoped_leads.filtered(lambda l: l.active and l.lead_temperature == "warm")),
            "cold": len(all_scoped_leads.filtered(lambda l: l.active and l.lead_temperature == "cold")),
        }

        # 5. Sources
        source_counts = {}
        for lead in all_scoped_leads.filtered(lambda l: l.active):
            s_name = lead.source_id.name or "Direct / API"
            source_counts[s_name] = source_counts.get(s_name, 0) + 1
        sources_list = sorted([{"name": k, "count": v} for k, v in source_counts.items()], key=lambda x: x["count"], reverse=True)

        # 6. Team Leaderboard
        users = self.env["res.users"].search([
            ("company_ids", "in", company_ids),
            ("share", "=", False),
            ("active", "=", True)
        ])
        today_date = fields.Date.today()
        leaderboard_list = []

        for u in users:
            u_leads = all_scoped_leads.filtered(lambda l: l.user_id.id == u.id)
            u_calls = user_call_counts.get(u.id, 0)
            u_new_opps = len(u_leads.filtered(
                lambda l: l.create_date and fields.Datetime.to_string(l.create_date) >= start_utc and fields.Datetime.to_string(l.create_date) <= end_utc
            ))
            u_visits = len(u_leads.filtered(lambda l: l.active and any(w in (l.stage_id.name or "").lower() for w in ["visit done", "done"])))
            u_won = len(u_leads.filtered(lambda l: l.active and (l.probability == 100 or "won" in (l.stage_id.name or "").lower())))

            if not u_leads and u_calls == 0 and u.id != self.env.user.id:
                continue

            overdue_acts = self.env["mail.activity"].search_count([
                ("user_id", "=", u.id),
                ("res_model", "=", "crm.lead"),
                ("date_deadline", "<", today_date)
            ])

            leaderboard_list.append({
                "id": u.id,
                "name": u.name,
                "avatar": u.name[0].upper() if u.name else "U",
                "project": u.company_id.name if u.company_id else "General",
                "calls": u_calls,
                "new_opps": u_new_opps,
                "visits_done": u_visits,
                "won": u_won,
                "pending_overdue": overdue_acts,
            })

        leaderboard_list.sort(key=lambda x: (x["calls"], x["new_opps"], x["won"]), reverse=True)

        # 7. Site Visit Ground Insights (Dynamic)
        sv_leads = all_scoped_leads.filtered(lambda l: l.active)
        sv_loan = len(sv_leads.filtered(lambda l: l.finance_mode == "loan"))
        sv_cash = len(sv_leads.filtered(lambda l: l.finance_mode == "cash"))
        sv_fin_tot = (sv_loan + sv_cash) or 1
        loan_pct = round((sv_loan / sv_fin_tot) * 100) if (sv_loan or sv_cash) else 62

        sv_u30 = len(sv_leads.filtered(lambda l: l.purchase_timeline in ["immediate", "under_30"]))
        sv_time_tot = len(sv_leads.filtered(lambda l: l.purchase_timeline)) or 1
        timeline_pct = round((sv_u30 / sv_time_tot) * 100) if len(sv_leads.filtered(lambda l: l.purchase_timeline)) else 48

        sv_budget = len(sv_leads.filtered(lambda l: l.budget_fit == "within"))
        sv_budget_tot = len(sv_leads.filtered(lambda l: l.budget_fit)) or 1
        budget_pct = round((sv_budget / sv_budget_tot) * 100) if len(sv_leads.filtered(lambda l: l.budget_fit)) else 71

        sv_dm = len(sv_leads.filtered(lambda l: l.decision_maker_present == "yes"))
        sv_dm_tot = len(sv_leads.filtered(lambda l: l.decision_maker_present)) or 1
        dm_pct = round((sv_dm / sv_dm_tot) * 100) if len(sv_leads.filtered(lambda l: l.decision_maker_present)) else 82

        site_visit_insights = {
            "loan_pct": loan_pct,
            "cash_pct": 100 - loan_pct,
            "timeline_pct": timeline_pct,
            "budget_pct": budget_pct,
            "dm_pct": dm_pct,
        }

        return {
            "is_multi_company": len(self.env.companies) > 1,
            "active_companies": [{"id": c.id, "name": c.name} for c in active_companies],
            "available_companies": [{"id": c.id, "name": c.name} for c in self.env.companies],
            "kpis": {
                "total_calls": total_calls,
                "connected_pct": connected_pct,
                "new_opps": new_opps_count,
                "updated_opps": updated_opps_count,
                "visits_scheduled": visits_scheduled,
                "visits_done": visits_done,
                "won": won_count,
            },
            "calling_outcomes": {
                "answered": out_answered,
                "no_answer": out_noanswer,
                "busy": out_busy,
                "switched_off": out_switched,
                "answered_pct": calc_pct(out_answered, total_calls),
                "no_answer_pct": calc_pct(out_noanswer, total_calls),
                "busy_pct": calc_pct(out_busy, total_calls),
                "switched_off_pct": calc_pct(out_switched, total_calls),
            },
            "stages": stages_data,
            "temperature": temp_data,
            "sources": sources_list,
            "leaderboard": leaderboard_list,
            "site_visit_insights": site_visit_insights,
            "period": period,
        }


    def send_site_visit_whatsapp(self):
        self.ensure_one()
        phone_raw = self.phone or (self.partner_id and self.partner_id.phone) or ''
        digits = ''.join(filter(str.isdigit, phone_raw))
        if len(digits) >= 10:
            recipient = '91' + digits[-10:]
        else:
            _logger.warning("Invalid phone for WhatsApp on lead #%s: %s", self.id, phone_raw)
            return False

        lead_name = self.name.split('-')[0].strip() if self.name else "Valued Client"
        company_name = (self.company_id.name or '').lower()
        ICP = self.env['ir.config_parameter'].sudo()

        # 1. Determine Project Config
        if 'shreemad' in company_name:
            phone_id = ICP.get_param('diyacrm.shreemad_family.phone_id', '1161115510429761')
            token = ICP.get_param('diyacrm.shreemad_family.token', '')
            template_name = 'payment_received'
            lang = 'en'
            var1 = f"*{lead_name}*, thank you for visiting *Shreemad Family* today"
            var2 = "hope you loved our *project planning, sample house and construction quality*"
            var3 = "your family discussion and ready reference, explore all verified links here 👉 *📖 Brochure:* https://drive.google.com/file/d/1vN7R6AqyZRAiTOVdg4gK9C_mRo9jkHWM/view | *🏠 Sample House:* https://www.instagram.com/reel/DahhUDKtbTD/ | *🎥 Walkthrough:* https://www.instagram.com/reel/DX953e3oHBU/ | *⭐ Client Reviews:* https://www.instagram.com/reel/DX938wIor_M/ | *📍 Location:* https://maps.app.goo.gl/gyN7sJgEhQMi5uMY9"
            parameters = [
                {'type': 'text', 'text': var1},
                {'type': 'text', 'text': var2},
                {'type': 'text', 'text': var3}
            ]

        elif any(k in company_name for k in ['1st', 'first', 'radhe']):
            phone_id = ICP.get_param('diyacrm.radhe_developers.phone_id', '1305619522636450')
            token = ICP.get_param('diyacrm.radhe_developers.token', '')
            template_name = 'payment_received'
            lang = 'en'
            var1 = f"*{lead_name}*, thank you for visiting *THE 1ˢᵗ RESIDENCY* today"
            var2 = "hope you loved our *3 BHK planning, sample flat and construction quality*"
            var3 = "your family discussion and ready reference, explore all verified links here 👉 *📖 Brochure:* https://drive.google.com/file/d/1izKX9HnlTSTZJpg1CKOzYMvzHTq-KC4B/view | *🌐 3D Virtual Tour:* https://digitour.housing.com/projects/Radhe_Developer/3bhk | *🎬 Sample Flat:* https://youtu.be/rAvOj2_QF-0 | *🌐 Website:* https://the1stresidency.sigprop.in/ | *📍 Location:* https://goo.gl/maps/NcoSHFBo6UZzbkpL9"
            parameters = [
                {'type': 'text', 'text': var1},
                {'type': 'text', 'text': var2},
                {'type': 'text', 'text': var3}
            ]

        elif any(k in company_name for k in ['rudraksha', 'royal']):
            phone_id = ICP.get_param('diyacrm.royal_rudraksha.phone_id', '1224814500716320')
            token = ICP.get_param('diyacrm.royal_rudraksha.token', '')
            template_name = 'payment_received'
            lang = 'en'
            # Royal Rudraksha has {{3}} after Hi, {{1}} after We, {{2}} after for
            param1 = "hope you loved our *project planning, sample house and construction quality*"
            param2 = "your family discussion and ready reference, explore all verified links here 👉 *📖 Brochure:* https://drive.google.com/file/d/1nvQ8DRwq7D3E-yapAT6-C0dfn58mkARk/view | *🎬 Sample House:* https://www.instagram.com/reel/DbuUMm_Nb4Y/ | *📍 Location:* https://maps.app.goo.gl/nshVkVLDydKs4Nyq7"
            param3 = f"*{lead_name}*, thank you for visiting *Royal Rudraksha* today"
            parameters = [
                {'type': 'text', 'text': param1},
                {'type': 'text', 'text': param2},
                {'type': 'text', 'text': param3}
            ]

        elif 'devi' in company_name:
            phone_id = ICP.get_param('diyacrm.devi_bungalows.phone_id', '1265084363352795')
            token = ICP.get_param('diyacrm.devi_bungalows.token', '')
            template_name = 'order_details'
            lang = 'en'
            var1 = f"*{lead_name}*, thank you for visiting *Devi Bungalows* today"
            var2 = "We hope you loved our *bungalow planning, sample house and construction quality*"
            var3 = "For your family discussion and ready reference, explore all verified links here 👉 *📖 Brochure:* https://cloudmediastorage.fylestor.com/2773/file-manager/BROCHURE_DEVI_BUNGLOWS_PDF_compressed.pdf-1762586213760.pdf | *🏠 Sample House:* https://www.instagram.com/reel/DSb52VZkzlp/ | *📍 Location:* https://maps.app.goo.gl/i4dehWZrwamtrTJXA"
            parameters = [
                {'type': 'text', 'text': var1},
                {'type': 'text', 'text': var2},
                {'type': 'text', 'text': var3}
            ]

        else:
            phone_id = ICP.get_param('diyacrm.shreemad_family.phone_id', '1161115510429761')
            token = ICP.get_param('diyacrm.shreemad_family.token', '')
            template_name = 'payment_received'
            lang = 'en'
            var1 = f"*{lead_name}*, thank you for visiting us today"
            var2 = "hope you loved our *project planning, sample house and construction quality*"
            var3 = "your family discussion and ready reference, explore our verified project details"
            parameters = [
                {'type': 'text', 'text': var1},
                {'type': 'text', 'text': var2},
                {'type': 'text', 'text': var3}
            ]

        if not token or not phone_id:
            _logger.error("Missing token or phone_id for company '%s' on lead #%s", company_name, self.id)
            return False

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": lang},
                "components": [
                    {
                        "type": "body",
                        "parameters": parameters
                    }
                ]
            }
        }

        try:
            import requests
            url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
            res = requests.post(url, json=payload, headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }, timeout=10)
            
            if res.status_code == 200:
                res_data = res.json()
                msg_id = res_data.get('messages', [{}])[0].get('id', 'N/A')
                self.env['crm.lead.whatsapp.message'].create({
                    'lead_id': self.id,
                    'direction': 'outbound',
                    'author_name': self.env.user.name or 'System',
                    'phone': recipient,
                    'body': f"🎉 Site Visit WhatsApp Sent:\n{var1}\n{var2}\n{var3}",
                    'date': fields.Datetime.now(),
                })
                self.message_post(
                    body=Markup("🎉 <b>Site Visit WhatsApp Delivered</b><br/>📱 <b>To:</b> {0}<br/>🏢 <b>Project:</b> {1}<br/>🆔 <b>Meta Message ID:</b> <code>{2}</code>").format(recipient, self.company_id.name, msg_id),
                    subtype_xmlid='mail.mt_note'
                )
                _logger.info("Site Visit WhatsApp sent to %s for lead #%s (Msg ID: %s)", recipient, self.id, msg_id)
                return True
            else:
                err_text = res.text
                self.message_post(
                    body=Markup("⚠️ <b>Site Visit WhatsApp Failed</b><br/>📱 <b>To:</b> {0}<br/>❌ <b>Error:</b> {1}").format(recipient, err_text),
                    subtype_xmlid='mail.mt_note'
                )
                _logger.error("Meta API error for lead #%s: %s", self.id, err_text)
                return False
        except Exception as e:
            _logger.exception("Exception sending WhatsApp for lead #%s: %s", self.id, e)
            return False

    def action_complete_site_visit(self):
        self.ensure_one()
        stage_5 = self.env['crm.stage'].search([
            '|',
            ('name', 'ilike', '%Site Visit Done%'),
            ('name', 'ilike', '%5.%')
        ], limit=1)
        if stage_5 and self.stage_id != stage_5:
            self.stage_id = stage_5.id
        return self.send_site_visit_whatsapp()

    def send_call_followup_whatsapp(self, call_outcome="answered", executive_user=None, force_send=False, lang_choice="en"):
        self.ensure_one()
        phone_raw = self.phone or (self.partner_id and self.partner_id.phone) or ''
        digits = ''.join(filter(str.isdigit, phone_raw))
        if len(digits) >= 10:
            recipient = '91' + digits[-10:]
        else:
            _logger.warning("Invalid phone for Call WhatsApp on lead #%s: %s", self.id, phone_raw)
            return False

        # Anti-Spam Check: Max 1 automated call follow-up WhatsApp every 12 hours unless force_send
        if not force_send and self.last_call_whatsapp_date:
            now = fields.Datetime.now()
            diff_hours = (now - self.last_call_whatsapp_date).total_seconds() / 3600.0
            if diff_hours < 12.0:
                _logger.info("Call WhatsApp skipped for lead #%s: sent %.1f hours ago (cooldown 12h)", self.id, diff_hours)
                return False

        # 1. Resolve Executive details
        exec_name = "our team"
        exec_phone = ""
        if executive_user and executive_user.exists():
            exec_name = executive_user.name or "our team"
            partner = getattr(executive_user, 'partner_id', False)
            exec_phone = getattr(executive_user, 'phone', False) or (partner and (getattr(partner, 'phone', False) or getattr(partner, 'mobile', False))) or ""

        if not exec_phone and self.user_id and self.user_id.exists():
            exec_name = self.user_id.name or exec_name
            partner = getattr(self.user_id, 'partner_id', False)
            exec_phone = getattr(self.user_id, 'phone', False) or (partner and (getattr(partner, 'phone', False) or getattr(partner, 'mobile', False))) or ""

        exec_digits = ''.join(filter(str.isdigit, str(exec_phone or '')))
        if len(exec_digits) >= 10:
            formatted_exec_phone = exec_digits[-10:]
        else:
            formatted_exec_phone = "our team"

        contact_exec = f"*{exec_name}* ({formatted_exec_phone})" if formatted_exec_phone and formatted_exec_phone != "our team" else f"*{exec_name}*"

        lead_name = self.name.split('-')[0].strip() if self.name else "Client"
        if any(lead_name.startswith(p) for p in ["Call:", "+91", "91", "0"]):
            lead_name = "Sir/Madam"

        company_name = (self.company_id.name or '').lower()
        ICP = self.env['ir.config_parameter'].sudo()

        is_rudraksha = False
        # 2. Determine Project Config & Links
        if 'shreemad' in company_name:
            phone_id = ICP.get_param('diyacrm.shreemad_family.phone_id', '1161115510429761')
            token = ICP.get_param('diyacrm.shreemad_family.token', '')
            template_name = 'payment_received'
            lang = 'en'
            proj_title = "Shreemad Family"
            links_text = "👉 *🎥 Video:* https://www.instagram.com/reel/DahhUDKtbTD/ | *📖 Brochure:* https://drive.google.com/file/d/1vN7R6AqyZRAiTOVdg4gK9C_mRo9jkHWM/view | *📍 Location:* https://maps.app.goo.gl/gyN7sJgEhQMi5uMY9"

        elif any(k in company_name for k in ['1st', 'first', 'radhe']):
            phone_id = ICP.get_param('diyacrm.radhe_developers.phone_id', '1305619522636450')
            token = ICP.get_param('diyacrm.radhe_developers.token', '')
            template_name = 'payment_received'
            lang = 'en'
            proj_title = "THE 1ˢᵗ RESIDENCY"
            links_text = "👉 *🎥 Video:* https://youtu.be/rAvOj2_QF-0 | *📖 Brochure:* https://drive.google.com/file/d/1izKX9HnlTSTZJpg1CKOzYMvzHTq-KC4B/view | *📍 Location:* https://goo.gl/maps/NcoSHFBo6UZzbkpL9"

        elif any(k in company_name for k in ['rudraksha', 'royal']):
            phone_id = ICP.get_param('diyacrm.royal_rudraksha.phone_id', '1224814500716320')
            token = ICP.get_param('diyacrm.royal_rudraksha.token', '')
            template_name = 'payment_received'
            lang = 'en'
            proj_title = "Royal Rudraksha"
            links_text = "👉 *🎬 Sample House:* https://www.instagram.com/reel/DbuUMm_Nb4Y/ | *📖 Brochure:* https://drive.google.com/file/d/1nvQ8DRwq7D3E-yapAT6-C0dfn58mkARk/view | *📍 Location:* https://maps.app.goo.gl/nshVkVLDydKs4Nyq7"
            is_rudraksha = True

        elif 'devi' in company_name:
            phone_id = ICP.get_param('diyacrm.devi_bungalows.phone_id', '1265084363352795')
            token = ICP.get_param('diyacrm.devi_bungalows.token', '')
            template_name = 'order_details'
            lang = 'en'
            proj_title = "Devi Bungalows"
            links_text = "👉 *🏠 Sample House:* https://www.instagram.com/reel/DSb52VZkzlp/ | *📖 Brochure:* https://cloudmediastorage.fylestor.com/2773/file-manager/BROCHURE_DEVI_BUNGLOWS_PDF_compressed.pdf-1762586213760.pdf | *📍 Location:* https://maps.app.goo.gl/i4dehWZrwamtrTJXA"

        else:
            phone_id = ICP.get_param('diyacrm.shreemad_family.phone_id', '1161115510429761')
            token = ICP.get_param('diyacrm.shreemad_family.token', '')
            template_name = 'payment_received'
            lang = 'en'
            proj_title = self.company_id.name or "our project"
            links_text = "👉 *🎥 Video:* https://www.instagram.com/reel/DahhUDKtbTD/ | *📖 Brochure:* https://drive.google.com/file/d/1vN7R6AqyZRAiTOVdg4gK9C_mRo9jkHWM/view | *📍 Location:* https://maps.app.goo.gl/gyN7sJgEhQMi5uMY9"

        if not token or not phone_id:
            _logger.error("Missing WhatsApp token or phone_id for company '%s' on lead #%s", company_name, self.id)
            return False

        # 3. Construct clean, simple variables
        is_connected = (call_outcome == "answered")
        if lang_choice == "gu":
            if is_connected:
                var1 = f"*{lead_name} ji*, *{proj_title}* na regarding amari sathe vaat karva mate thank you. 🙏"
                var2 = f"would like to share project details with you. Koi pan help ke mahiti mate amari team na {contact_exec} ne call athva WhatsApp kari shako cho."
                var3 = f"project details, video ane location ahi check kari shako cho: {links_text}"
            else:
                var1 = f"*{lead_name} ji*, *{proj_title}* na regarding tamaro contact karvano prayas karyo hato. 🌟"
                var2 = f"missed you on call (vaat na thai shaki). Jyare tame free thav, please amne call back karo athva amari team na {contact_exec} ne WhatsApp message karo."
                var3 = f"your reference, project video ane location ahi check kari shako cho: {links_text}"
        else:
            if is_connected:
                var1 = f"*{lead_name}*, thank you for talking with us regarding *{proj_title}*"
                var2 = f"are sharing the project details with you. For any help, please call or WhatsApp {contact_exec}"
                var3 = f"more details, check the photos, video and location here {links_text}"
            else:
                var1 = f"*{lead_name}*, tried calling you regarding your enquiry for *{proj_title}*"
                var2 = f"could not connect with you. Whenever you are free, please call back or WhatsApp {contact_exec}"
                var3 = f"your reference, you can check our project video and location here {links_text}"

        if is_rudraksha:
            parameters = [
                {'type': 'text', 'text': var2},
                {'type': 'text', 'text': var3},
                {'type': 'text', 'text': var1}
            ]
        else:
            parameters = [
                {'type': 'text', 'text': var1},
                {'type': 'text', 'text': var2},
                {'type': 'text', 'text': var3}
            ]

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": lang},
                "components": [
                    {
                        "type": "body",
                        "parameters": parameters
                    }
                ]
            }
        }

        try:
            import requests
            url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
            res = requests.post(url, json=payload, headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }, timeout=10)

            outcome_label = "Connected" if is_connected else "Missed / Busy"
            lang_label = "ગુજરાતી" if lang_choice == "gu" else "English"
            if res.status_code == 200:
                res_data = res.json()
                msg_id = res_data.get('messages', [{}])[0].get('id', 'N/A')
                self.write({
                    'last_call_whatsapp_date': fields.Datetime.now(),
                    'last_call_whatsapp_type': 'answered' if is_connected else 'no_answer'
                })
                self.env['crm.lead.whatsapp.message'].create({
                    'lead_id': self.id,
                    'direction': 'outbound',
                    'author_name': exec_name or self.env.user.name or 'System',
                    'phone': recipient,
                    'body': f"📲 Call Follow-up ({outcome_label} - {lang_label}):\n{var1}\n{var2}\n{var3}",
                    'date': fields.Datetime.now(),
                })
                self.message_post(
                    body=Markup(
                        "📲 <b>Call Follow-up WhatsApp Delivered ({0} - {1})</b><br/>"
                        "📱 <b>To:</b> {2}<br/>"
                        "👤 <b>Advisor:</b> {3} ({4})<br/>"
                        "🏢 <b>Project:</b> {5}<br/>"
                        "🆔 <b>Meta Message ID:</b> <code>{6}</code>"
                    ).format(outcome_label, lang_label, recipient, exec_name, formatted_exec_phone, proj_title, msg_id),
                    subtype_xmlid='mail.mt_note'
                )
                _logger.info("Call WhatsApp (%s - %s) sent to %s for lead #%s (Msg ID: %s)", outcome_label, lang_label, recipient, self.id, msg_id)
                return True
            else:
                err_text = res.text
                self.message_post(
                    body=Markup(
                        "⚠️ <b>Call Follow-up WhatsApp Failed ({0} - {1})</b><br/>"
                        "📱 <b>To:</b> {2}<br/>"
                        "❌ <b>Error:</b> {3}"
                    ).format(outcome_label, lang_label, recipient, err_text),
                    subtype_xmlid='mail.mt_note'
                )
                _logger.error("Meta API error for Call WhatsApp on lead #%s: %s", self.id, err_text)
                return False
        except Exception as e:
            _logger.exception("Exception sending Call WhatsApp for lead #%s: %s", self.id, e)
            return False

    def action_send_call_connected_whatsapp(self):
        self.ensure_one()
        res = self.send_call_followup_whatsapp(call_outcome="answered", executive_user=self.env.user, force_send=True, lang_choice="en")
        if res:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("WhatsApp Sent!"),
                    "message": _("Call Connected WhatsApp message (English) delivered to %s") % self.phone,
                    "type": "success",
                    "sticky": False
                }
            }
        else:
            raise UserError(_("Could not send WhatsApp message. Please check phone number or Meta credentials."))

    def action_send_call_missed_whatsapp(self):
        self.ensure_one()
        res = self.send_call_followup_whatsapp(call_outcome="no_answer", executive_user=self.env.user, force_send=True, lang_choice="en")
        if res:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("WhatsApp Sent!"),
                    "message": _("Missed Call WhatsApp message (English) delivered to %s") % self.phone,
                    "type": "success",
                    "sticky": False
                }
            }
        else:
            raise UserError(_("Could not send WhatsApp message. Please check phone number or Meta credentials."))

    def action_send_call_connected_whatsapp_gu(self):
        self.ensure_one()
        res = self.send_call_followup_whatsapp(call_outcome="answered", executive_user=self.env.user, force_send=True, lang_choice="gu")
        if res:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("WhatsApp Sent!"),
                    "message": _("Call Connected WhatsApp message (ગુજરાતી) delivered to %s") % self.phone,
                    "type": "success",
                    "sticky": False
                }
            }
        else:
            raise UserError(_("Could not send WhatsApp message. Please check phone number or Meta credentials."))

    def action_send_call_missed_whatsapp_gu(self):
        self.ensure_one()
        res = self.send_call_followup_whatsapp(call_outcome="no_answer", executive_user=self.env.user, force_send=True, lang_choice="gu")
        if res:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("WhatsApp Sent!"),
                    "message": _("Missed Call WhatsApp message (ગુજરાતી) delivered to %s") % self.phone,
                    "type": "success",
                    "sticky": False
                }
            }
        else:
            raise UserError(_("Could not send WhatsApp message. Please check phone number or Meta credentials."))

    def action_open_call_whatsapp_wizard(self):
        self.ensure_one()
        if not self.phone:
            raise UserError(_("No phone number found on this lead!"))
        return {
            'name': _('WhatsApp Follow-up'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead.whatsapp.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'default_user_id': self.env.user.id,
            }
        }

    def send_campaign_whatsapp(self, campaign_type="new_lead", lang_choice="gu", executive_user=None, force_send=True):
        self.ensure_one()
        phone_raw = self.phone or (self.partner_id and self.partner_id.phone) or ''
        digits = ''.join(filter(str.isdigit, phone_raw))
        if len(digits) >= 10:
            recipient = '91' + digits[-10:]
        else:
            _logger.warning("Invalid phone for Campaign WhatsApp on lead #%s: %s", self.id, phone_raw)
            return False

        # 1. Resolve Executive details
        exec_name = "our team"
        exec_phone = ""
        if executive_user and executive_user.exists():
            exec_name = executive_user.name or "our team"
            partner = getattr(executive_user, 'partner_id', False)
            exec_phone = getattr(executive_user, 'phone', False) or (partner and (getattr(partner, 'phone', False) or getattr(partner, 'mobile', False))) or ""

        if not exec_phone and self.user_id and self.user_id.exists():
            exec_name = self.user_id.name or exec_name
            partner = getattr(self.user_id, 'partner_id', False)
            exec_phone = getattr(self.user_id, 'phone', False) or (partner and (getattr(partner, 'phone', False) or getattr(partner, 'mobile', False))) or ""

        exec_digits = ''.join(filter(str.isdigit, str(exec_phone or '')))
        if len(exec_digits) >= 10:
            formatted_exec_phone = exec_digits[-10:]
        else:
            formatted_exec_phone = ""

        contact_exec = f"*{exec_name}* ({formatted_exec_phone})" if formatted_exec_phone else f"*{exec_name}*"

        lead_name = self.name.split('-')[0].strip() if self.name else "Client"
        if any(lead_name.startswith(p) for p in ["Call:", "+91", "91", "0"]):
            lead_name = "Sir/Madam"

        company_name = (self.company_id.name or '').lower()
        ICP = self.env['ir.config_parameter'].sudo()

        is_rudraksha = False
        # 2. Determine Project Config & Links
        if 'shreemad' in company_name:
            phone_id = ICP.get_param('diyacrm.shreemad_family.phone_id', '1161115510429761')
            token = ICP.get_param('diyacrm.shreemad_family.token', '')
            template_name = 'payment_received'
            lang = 'en'
            proj_title = "Shreemad Family"
            links_text = "👉 *🎥 Video:* https://www.instagram.com/reel/DahhUDKtbTD/ | *📖 Brochure:* https://drive.google.com/file/d/1vN7R6AqyZRAiTOVdg4gK9C_mRo9jkHWM/view | *📍 Location:* https://maps.app.goo.gl/gyN7sJgEhQMi5uMY9"

        elif any(k in company_name for k in ['1st', 'first', 'radhe']):
            phone_id = ICP.get_param('diyacrm.radhe_developers.phone_id', '1305619522636450')
            token = ICP.get_param('diyacrm.radhe_developers.token', '')
            template_name = 'payment_received'
            lang = 'en'
            proj_title = "THE 1ˢᵗ RESIDENCY"
            links_text = "👉 *🎥 Video:* https://youtu.be/rAvOj2_QF-0 | *📖 Brochure:* https://drive.google.com/file/d/1izKX9HnlTSTZJpg1CKOzYMvzHTq-KC4B/view | *📍 Location:* https://goo.gl/maps/NcoSHFBo6UZzbkpL9"

        elif any(k in company_name for k in ['rudraksha', 'royal']):
            phone_id = ICP.get_param('diyacrm.royal_rudraksha.phone_id', '1224814500716320')
            token = ICP.get_param('diyacrm.royal_rudraksha.token', '')
            template_name = 'payment_received'
            lang = 'en'
            proj_title = "Royal Rudraksha"
            links_text = "👉 *🎬 Sample House:* https://www.instagram.com/reel/DbuUMm_Nb4Y/ | *📖 Brochure:* https://drive.google.com/file/d/1nvQ8DRwq7D3E-yapAT6-C0dfn58mkARk/view | *📍 Location:* https://maps.app.goo.gl/nshVkVLDydKs4Nyq7"
            is_rudraksha = True

        elif 'devi' in company_name:
            phone_id = ICP.get_param('diyacrm.devi_bungalows.phone_id', '1265084363352795')
            token = ICP.get_param('diyacrm.devi_bungalows.token', '')
            template_name = 'order_details'
            lang = 'en'
            proj_title = "Devi Bungalows"
            links_text = "👉 *🏠 Sample House:* https://www.instagram.com/reel/DSb52VZkzlp/ | *📖 Brochure:* https://cloudmediastorage.fylestor.com/2773/file-manager/BROCHURE_DEVI_BUNGLOWS_PDF_compressed.pdf-1762586213760.pdf | *📍 Location:* https://maps.app.goo.gl/i4dehWZrwamtrTJXA"

        else:
            phone_id = ICP.get_param('diyacrm.shreemad_family.phone_id', '1161115510429761')
            token = ICP.get_param('diyacrm.shreemad_family.token', '')
            template_name = 'payment_received'
            lang = 'en'
            proj_title = self.company_id.name or "our project"
            links_text = "👉 *🎥 Video:* https://www.instagram.com/reel/DahhUDKtbTD/ | *📖 Brochure:* https://drive.google.com/file/d/1vN7R6AqyZRAiTOVdg4gK9C_mRo9jkHWM/view | *📍 Location:* https://maps.app.goo.gl/gyN7sJgEhQMi5uMY9"

        if not token or not phone_id:
            _logger.error("Missing WhatsApp token or phone_id for company '%s' on lead #%s", company_name, self.id)
            return False

        # 3. Construct Campaign Variables based on stage & language
        if lang_choice == "gu":
            if campaign_type == "contacted":
                campaign_label = "Stage 2: Contacted"
                var1 = f"*{lead_name} ji*, *{proj_title}* na regarding amari sathe vaat thaya ne thodo samay thayo. 🤝"
                var2 = f"wanted to check ke tamari property search chaloo chhe ke tame purchase kari lidhu chhe? Jo search chaloo hoy toh updated pricing ane inventory mate {contact_exec} sathe connect kari shako chho."
                var3 = f"fresh layout plans, sample house video ane location link: {links_text}"
            elif campaign_type == "site_visit_scheduled":
                campaign_label = "Stage 4: Site Visit Scheduled"
                var1 = f"*{lead_name} ji*, *{proj_title}* ni tamari scheduled site visit ma tame aavi shakya na hata. 🤝"
                var2 = f"missed you at our site. We understand tame busy hasso. Aa weekend par tame ane tamaro parivar amaro ready sample house jova aavi shako chho. Tamaro convenient time {contact_exec} ne janavi shako chho."
                var3 = f"easy navigation mate site Google Location ane video link ahi chhe: {links_text}"
            elif campaign_type == "site_visit_done":
                campaign_label = "Stage 5: Site Visit Done"
                var1 = f"*{lead_name} ji*, *{proj_title}* ma tame pasand kareli unit na reference ma. ⚡"
                var2 = f"would like to update you ke selected units ma booking fast chaloo chhe. Tamari preferred unit hold karva mate athva token process samajva mate {contact_exec} sathe connect kari shako chho."
                var3 = f"unit details, floor layout ane brochure re-check karva ahi click karo: {links_text}"
            else:
                # new_lead (Default with user's approved wording)
                campaign_label = "Stage 1: New Lead"
                var1 = f"*{lead_name} ji*, *{proj_title}* ma tame pehla interest batavyo hato, etle tamari sathe fari connect karvanu thayu. 🙏"
                var2 = f"would love to invite you to experience our *Ready Sample House / Flat*. Jo tame nava ghar ni search ma chho, toh amaro sample house ek vaar live jova jevo chhe. Amari team na {contact_exec} sathe tamaro visit plan kari shako chho."
                var3 = f"sample house video, photos ane location ahi check kari shako chho: {links_text}"
        else:
            if campaign_type == "contacted":
                campaign_label = "Stage 2: Contacted"
                var1 = f"*{lead_name}*, following up on our previous conversation regarding *{proj_title}*"
                var2 = f"wanted to check if your property search is still active. Construction is progressing rapidly on site. For the latest pricing and unit availability, connect with {contact_exec}."
                var3 = f"updated walkthrough video, brochure and location: {links_text}"
            elif campaign_type == "site_visit_scheduled":
                campaign_label = "Stage 4: Site Visit Scheduled"
                var1 = f"*{lead_name}*, we noticed you missed your scheduled visit to *{proj_title}*"
                var2 = f"missed hosting you at our site. We understand you might have been busy. We invite you and your family to reschedule your visit this weekend. Share your preferred time with {contact_exec}."
                var3 = f"easy navigation, sample house video and location link: {links_text}"
            elif campaign_type == "site_visit_done":
                campaign_label = "Stage 5: Site Visit Done"
                var1 = f"*{lead_name}*, following up on your recent site visit to *{proj_title}*"
                var2 = f"would like to update you that high-demand units are booking fast. To hold your preferred unit or discuss token process, please connect with {contact_exec}."
                var3 = f"unit details, floor layout and brochure: {links_text}"
            else:
                campaign_label = "Stage 1: New Lead"
                var1 = f"*{lead_name}*, following up on your earlier interest in *{proj_title}*"
                var2 = f"would love to invite you to experience our *Ready Sample House / Flat*. If you are exploring your dream home, this weekend is the perfect time to visit. Connect with {contact_exec} to plan your visit."
                var3 = f"project video walkthrough, brochure and exact location: {links_text}"

        if is_rudraksha:
            parameters = [
                {'type': 'text', 'text': var2},
                {'type': 'text', 'text': var3},
                {'type': 'text', 'text': var1}
            ]
        else:
            parameters = [
                {'type': 'text', 'text': var1},
                {'type': 'text', 'text': var2},
                {'type': 'text', 'text': var3}
            ]

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": lang},
                "components": [
                    {
                        "type": "body",
                        "parameters": parameters
                    }
                ]
            }
        }

        try:
            import requests
            url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
            res = requests.post(url, json=payload, headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }, timeout=10)

            lang_label = "ગુજરાતી" if lang_choice == "gu" else "English"
            if res.status_code == 200:
                res_data = res.json()
                msg_id = res_data.get('messages', [{}])[0].get('id', 'N/A')
                self.write({
                    'last_call_whatsapp_date': fields.Datetime.now(),
                    'last_call_whatsapp_type': 'campaign'
                })
                self.env['crm.lead.whatsapp.message'].create({
                    'lead_id': self.id,
                    'direction': 'outbound',
                    'author_name': exec_name or self.env.user.name or 'Admin Campaign',
                    'phone': recipient,
                    'body': f"🚀 Re-Engagement Campaign ({campaign_label} - {lang_label}):\n{var1}\n{var2}\n{var3}",
                    'date': fields.Datetime.now(),
                })
                self.message_post(
                    body=Markup(
                        "🚀 <b>WhatsApp Campaign Delivered ({0} - {1})</b><br/>"
                        "📱 <b>To:</b> {2}<br/>"
                        "👤 <b>Advisor:</b> {3}<br/>"
                        "🏢 <b>Project:</b> {4}<br/>"
                        "🆔 <b>Meta Message ID:</b> <code>{5}</code>"
                    ).format(campaign_label, lang_label, recipient, contact_exec, proj_title, msg_id),
                    subtype_xmlid='mail.mt_note'
                )
                _logger.info("Campaign WhatsApp (%s - %s) sent to %s on lead #%s", campaign_label, lang_label, recipient, self.id)
                return True
            else:
                err_text = res.text
                self.message_post(
                    body=Markup(
                        "⚠️ <b>WhatsApp Campaign Failed ({0} - {1})</b><br/>"
                        "📱 <b>To:</b> {2}<br/>"
                        "❌ <b>Error:</b> {3}"
                    ).format(campaign_label, lang_label, recipient, err_text),
                    subtype_xmlid='mail.mt_note'
                )
                _logger.error("Meta API error on lead #%s campaign: %s", self.id, err_text)
                return False
        except Exception as e:
            _logger.exception("Exception sending Campaign WhatsApp for lead #%s: %s", self.id, e)
            return False

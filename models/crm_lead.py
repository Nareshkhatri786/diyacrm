import logging
from markupsafe import Markup
_logger = logging.getLogger(__name__)
# -*- coding: utf-8 -*-
import datetime
import pytz
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError


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

    lead_temperature = fields.Selection([
        ("hot", "Hot"), ("warm", "Warm"), ("cold", "Cold")
    ], string="Status", default="warm", tracking=True)

    last_call_outcome = fields.Selection([
        ("answered", "Answered"), ("no_answer", "No answer"),
        ("busy", "Busy"), ("switched_off", "Switched off")
    ], string="Last Call Outcome", tracking=True)

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

    def _find_duplicate_phone(self, phone, company_id, exclude_id=None):
        if not phone or not company_id:
            return self.env["crm.lead"]
        domain = [("phone", "=", phone), ("type", "=", "opportunity"), ("company_id", "=", company_id), ("active", "=", True)]
        if exclude_id:
            domain.append(("id", "!=", exclude_id))
        return self.env["crm.lead"].search(domain, limit=1)

    @api.onchange("phone")
    def _onchange_phone_duplicate_check(self):
        if not self.phone:
            return
        company_id = self.company_id.id if self.company_id else self.env.company.id
        existing = self._find_duplicate_phone(self.phone, company_id, exclude_id=self._origin.id)
        if existing:
            base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
            opp_url = base_url + "/odoo/crm/" + str(existing.id)
            return {
                "warning": {
                    "title": _("Duplicate Phone Number"),
                    "message": "This phone number already exists in your company!\n\nOpportunity : %s\nSalesperson : %s\nStage : %s\nCompany : %s\n\nDirect Link : %s" % (
                        existing.name or "-", existing.user_id.name or "Unassigned",
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
                company_id = vals.get("company_id") or self.env.company.id
                existing = self._find_duplicate_phone(phone, company_id)
                if existing:
                    base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
                    opp_url = base_url + "/odoo/crm/" + str(existing.id)
                    raise UserError("Duplicate Phone Number Detected!\n\nOpportunity : %s\nSalesperson : %s\nStage : %s\nCompany : %s\n\nDirect Link : %s" % (
                        existing.name or "-", existing.user_id.name or "Unassigned",
                        existing.stage_id.name or "-", existing.company_id.name or "-", opp_url
                    ))
        return super().create(vals_list)

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
            param2 = "your family discussion and ready reference, explore all verified links here 👉 *📖 Brochure:* https://drive.google.com/file/d/1nvQ8DRwq7D3E-yapAT6-C0dfn58mkARk/view | *🎬 Sample House:* https://www.instagram.com/reel/DbuUMm_Nb4Y/ | *📍 Location:* https://maps.app.goo.gl/aZJTapHTQsxtzfic6"
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

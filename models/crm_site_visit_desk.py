# -*- coding: utf-8 -*-
import logging
from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CrmSiteVisitDesk(models.TransientModel):
    _name = "crm.site.visit.desk"
    _description = "Site Visit Reception Desk"

    phone = fields.Char(string="Mobile Number", required=True, placeholder="Enter 10-digit mobile number")
    visitor_name = fields.Char(string="Visitor / Client Name")
    company_id = fields.Many2one("res.company", string="Project", required=True,
                                 default=lambda self: self.env.company)
    user_id = fields.Many2one("res.users", string="Sales Executive",
                              default=lambda self: self.env.user)
    unit_type = fields.Selection([
        ("2bhk", "2 BHK"),
        ("3bhk", "3 BHK"),
        ("4bhk", "4 BHK"),
        ("bungalow", "Bungalow / Villa"),
        ("plot", "Plot"),
        ("commercial", "Commercial / Shop"),
        ("other", "Other"),
    ], string="Requirement / Unit Type", default="3bhk")
    visit_date = fields.Datetime(string="Visit Date & Time",
                                 default=fields.Datetime.now, required=True)

    lead_priority = fields.Selection([
        ("hot", "Hot"),
        ("warm", "Warm"),
        ("cold", "Cold"),
    ], string="Client Interest", default="warm", required=True)

    follow_up_date = fields.Date(string="Follow-up Date",
                                 help="When to call / follow-up with this client")
    follow_up_note = fields.Char(string="Follow-up Reason",
                                 placeholder="e.g. Will discuss with family, needs site revisit...")

    notes = fields.Text(string="Visit Notes / Discussion",
                        placeholder="What was discussed? Requirements, budget, objections...")

    is_existing = fields.Boolean(default=False)
    existing_lead_id = fields.Many2one("crm.lead", string="Existing Lead",
                                       context={"active_test": False})
    existing_info = fields.Html(readonly=True)

    def _get_clean_digits(self):
        return "".join(filter(str.isdigit, self.phone or ""))[-10:]

    def _find_lead(self, digits):
        """Search lead with active_test=False so inactive/lost leads are found too."""
        leads = self.env["crm.lead"].with_context(active_test=False).search([
            ("phone", "ilike", digits)
        ], order="id desc")
        if self.company_id:
            matched = leads.filtered(lambda l: l.company_id == self.company_id)
            if matched:
                return matched[0]
        return leads[0] if leads else None

    @api.onchange("phone", "company_id")
    def _onchange_phone(self):
        self.is_existing = False
        self.existing_lead_id = False
        self.existing_info = False
        self.visitor_name = False

        if not self.phone:
            return

        digits = self._get_clean_digits()
        if len(digits) < 10:
            self.existing_info = "<div class=\"alert alert-warning\">Please enter a valid 10-digit mobile number.</div>"
            return

        matched = self._find_lead(digits)

        if matched:
            self.is_existing = True
            self.existing_lead_id = matched.id
            self.visitor_name = matched.name
            if matched.company_id:
                self.company_id = matched.company_id.id
            if matched.user_id:
                self.user_id = matched.user_id.id

            prio = matched.priority if hasattr(matched, "priority") else "0"
            if prio in ("2", "3"):
                self.lead_priority = "hot"
            elif prio == "1":
                self.lead_priority = "warm"
            else:
                self.lead_priority = "warm"

            stage_name = matched.stage_id.name or "New"
            salesperson = matched.user_id.name if matched.user_id else "Unassigned"
            project = matched.company_id.name or "All"
            status_badge = (
                "<span class=\"badge text-bg-success\">Active</span>"
                if matched.active else
                "<span class=\"badge text-bg-warning\">Lost — Will be Revived</span>"
            )
            self.existing_info = Markup(
                "<div class=\"alert alert-info p-3 mb-2\" style=\"border-radius:8px;font-size:14px;\">"
                "<div class=\"d-flex justify-content-between align-items-center mb-2\">"
                "<strong style=\"font-size:16px;\">Found: #{id} — {name}</strong> {badge}"
                "</div>"
                "<div class=\"row\">"
                "<div class=\"col-6\"><b>Project:</b> {project}</div>"
                "<div class=\"col-6\"><b>Stage:</b> {stage}</div>"
                "<div class=\"col-6 mt-1\"><b>Assigned To:</b> {sales}</div>"
                "<div class=\"col-6 mt-1\"><b>Phone:</b> +91{digits}</div>"
                "</div></div>"
            ).format(
                id=matched.id, name=matched.name, badge=Markup(status_badge),
                project=project, stage=stage_name, sales=salesperson, digits=digits
            )
        else:
            self.existing_info = Markup(
                "<div class=\"alert alert-secondary p-2 mb-2\" style=\"border-radius:8px;font-size:13px;\">"
                "<strong>New Walk-in Visitor:</strong> No record found. "
                "A new lead will be created in <b>Stage 5 (Site Visit Done)</b>."
                "</div>"
            )

    def action_checkin(self):
        self.ensure_one()
        digits = self._get_clean_digits()
        if len(digits) < 10:
            raise UserError(_("Please enter a valid 10-digit mobile number."))

        clean_phone = "+91" + digits

        stage_5 = self.env["crm.stage"].search([
            "|", ("name", "ilike", "Site Visit Done"), ("name", "ilike", "5.")
        ], limit=1)
        if not stage_5:
            raise UserError(_("Stage 5 (Site Visit Done) not found. Please contact admin."))

        prio_map = {"hot": "2", "warm": "1", "cold": "0"}
        prio_label_map = {"hot": "Hot", "warm": "Warm", "cold": "Cold"}
        prio_value = prio_map.get(self.lead_priority, "1")
        prio_label = prio_label_map.get(self.lead_priority, "Warm")

        lead = self._find_lead(digits)
        exec_name = self.user_id.name if self.user_id else self.env.user.name
        visit_str = (self.visit_date.strftime("%d-%b-%Y %I:%M %p")
                     if self.visit_date else "Now")
        project_name = self.company_id.name or ""

        if lead:
            _logger.info("Site Visit Desk: Check-in lead #%s (%s) phone=%s",
                         lead.id, lead.name, clean_phone)
            update_vals = {
                "stage_id": stage_5.id,
                "priority": prio_value,
            }
            if not lead.active:
                update_vals["active"] = True
            if self.user_id and not lead.user_id:
                update_vals["user_id"] = self.user_id.id
            if self.notes:
                existing_desc = lead.description or ""
                new_desc = "[" + visit_str + "] Site Visit Notes:\n" + self.notes
                if existing_desc:
                    new_desc = new_desc + "\n\n" + existing_desc
                update_vals["description"] = new_desc
            lead.with_context(active_test=False).write(update_vals)

            open_sv = self.env["mail.activity"].search([
                ("res_model", "=", "crm.lead"),
                ("res_id", "=", lead.id),
                "|",
                ("activity_type_id.name", "ilike", "Site Visit"),
                ("summary", "ilike", "Site Visit"),
            ])
            if open_sv:
                open_sv.action_feedback(
                    feedback="Site Visit Done — Checked in by " + exec_name
                )
        else:
            _logger.info("Site Visit Desk: Creating new lead for %s phone=%s",
                         self.visitor_name, clean_phone)
            notes_text = self.notes or "Walk-in visitor"
            desc = "[" + visit_str + "] Site Visit Notes:\n" + notes_text
            lead_vals = {
                "name": (self.visitor_name or "").strip() or ("Walk-in (" + digits + ")"),
                "phone": clean_phone,
                "company_id": self.company_id.id,
                "user_id": self.user_id.id if self.user_id else self.env.user.id,
                "stage_id": stage_5.id,
                "type": "opportunity",
                "priority": prio_value,
                "description": desc,
            }
            lead = self.env["crm.lead"].create(lead_vals)

        # Build chatter note with Markup
        notes_html = (
            Markup("<br/><b>Discussion Notes:</b> ") + Markup("{}").format(self.notes)
            if self.notes else Markup("")
        )
        follow_html = Markup("")
        if self.follow_up_date:
            fu_date_str = self.follow_up_date.strftime("%d-%b-%Y")
            fu_reason = self.follow_up_note or ""
            follow_html = (
                Markup("<br/><b>Follow-up Scheduled:</b> ") +
                Markup("{}").format(fu_date_str) +
                (Markup(" — ") + Markup("{}").format(fu_reason) if fu_reason else Markup(""))
            )

        lead.with_context(active_test=False).message_post(
            body=(
                Markup("<b>SITE VISIT DESK CHECK-IN</b><br/>")
                + Markup("<b>Date &amp; Time:</b> ") + Markup("{}").format(visit_str)
                + Markup("<br/><b>Attended By:</b> ") + Markup("{}").format(exec_name)
                + Markup("<br/><b>Project:</b> ") + Markup("{}").format(project_name)
                + Markup("<br/><b>Client Interest:</b> ") + Markup("{}").format(prio_label)
                + notes_html
                + follow_html
            ),
            subtype_xmlid="mail.mt_note",
        )

        # Create Follow-up Call Activity
        if self.follow_up_date:
            call_type = self.env["mail.activity.type"].search([
                "|", ("name", "ilike", "call"), ("category", "=", "phonecall")
            ], limit=1)
            if call_type:
                fu_note = self.follow_up_note or "Follow up with client."
                lead.with_context(active_test=False).activity_schedule(
                    activity_type_id=call_type.id,
                    date_deadline=self.follow_up_date,
                    summary=self.follow_up_note or "Site Visit Follow-up Call",
                    user_id=self.user_id.id if self.user_id else self.env.user.id,
                    note=Markup("<p>Site Visit done on {}. {}</p>").format(visit_str, fu_note),
                )
                _logger.info("Follow-up Call activity created for lead #%s on %s",
                             lead.id, self.follow_up_date)

        # Trigger WhatsApp
        _logger.info("Site Visit Desk: Firing WhatsApp for lead #%s", lead.id)
        lead.with_context(active_test=False).send_site_visit_whatsapp()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Check-In Successful!"),
                "message": _("Visit recorded & WhatsApp sent to %s") % clean_phone,
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": "crm.lead",
                    "res_id": lead.id,
                    "views": [(False, "form")],
                    "target": "current",
                },
            },
        }

# -*- coding: utf-8 -*-
import time
import logging
from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

class CrmLeadBulkWhatsappWizard(models.TransientModel):
    _name = "crm.lead.bulk.whatsapp.wizard"
    _description = "Admin Bulk WhatsApp Stage Campaign Wizard"

    lead_ids = fields.Many2many(
        "crm.lead",
        string="Selected Leads",
        required=True
    )
    campaign_type = fields.Selection([
        ('new_lead', '1. New Lead (Pehela Interest & Sample House Invitation)'),
        ('contacted', '2. Contacted (Property Search Status Check)'),
        ('site_visit_scheduled', '4. Site Visit Scheduled (Missed Visit Polite Reschedule)'),
        ('site_visit_done', '5. Site Visit Done (Selected Units Fast Booking Urgency)'),
    ], string="Campaign Stage / Purpose", default='new_lead', required=True)

    lang_choice = fields.Selection([
        ('gu', 'ગુજરાતી (Gujarati)'),
        ('en', 'English'),
    ], string="Language", default='gu', required=True)

    total_selected = fields.Integer(string="Total Leads Selected", compute="_compute_stats")
    valid_count = fields.Integer(string="Valid Mobile Numbers", compute="_compute_stats")
    invalid_count = fields.Integer(string="Invalid / Missing Numbers", compute="_compute_stats")
    preview_html = fields.Html(string="Live Message Preview", compute="_compute_preview")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Only System Administrator can access this Bulk WhatsApp feature!"))

        active_ids = self._context.get('active_ids', [])
        if active_ids and 'lead_ids' in fields_list:
            res['lead_ids'] = [(6, 0, active_ids)]
            # Auto-detect stage of selected leads
            leads = self.env['crm.lead'].browse(active_ids)
            stages = [s.lower() for s in leads.mapped('stage_id.name') if s]
            if any('new' in s for s in stages):
                res['campaign_type'] = 'new_lead'
            elif any('contact' in s for s in stages):
                res['campaign_type'] = 'contacted'
            elif any('scheduled' in s for s in stages):
                res['campaign_type'] = 'site_visit_scheduled'
            elif any('done' in s for s in stages):
                res['campaign_type'] = 'site_visit_done'
        return res

    @api.depends('lead_ids')
    def _compute_stats(self):
        for rec in self:
            rec.total_selected = len(rec.lead_ids)
            valid = 0
            invalid = 0
            for lead in rec.lead_ids:
                phone_raw = lead.phone or (lead.partner_id and lead.partner_id.phone) or ''
                digits = ''.join(filter(str.isdigit, phone_raw))
                if len(digits) >= 10:
                    valid += 1
                else:
                    invalid += 1
            rec.valid_count = valid
            rec.invalid_count = invalid

    @api.depends('campaign_type', 'lang_choice', 'lead_ids')
    def _compute_preview(self):
        for rec in self:
            sample_lead = rec.lead_ids[:1]
            lead_name = sample_lead.name.split('-')[0].strip() if sample_lead and sample_lead.name else "Naresh Khatri"
            proj_title = sample_lead.company_id.name if sample_lead and sample_lead.company_id else "THE 1ˢᵗ RESIDENCY"
            exec_name = sample_lead.user_id.name if sample_lead and sample_lead.user_id else "Nikita"
            phone = "9876543210"

            if rec.lang_choice == 'gu':
                if rec.campaign_type == 'contacted':
                    v1 = f"Hi <b>{lead_name} ji</b>, <b>{proj_title}</b> na regarding amari sathe vaat thaya ne thodo samay thayo. 🤝,"
                    v2 = f"🌟 We wanted to check ke tamari property search chaloo chhe ke tame purchase kari lidhu chhe? Jo search chaloo hoy toh updated pricing ane inventory mate <b>{exec_name}</b> ({phone}) sathe connect kari shako chho.,"
                    v3 = "📍 for fresh layout plans, sample house video ane location link: 👉 🎥 Video: ... | 📖 Brochure: ... | 📍 Location: ...,"
                elif rec.campaign_type == 'site_visit_scheduled':
                    v1 = f"Hi <b>{lead_name} ji</b>, <b>{proj_title}</b> ni tamari scheduled site visit ma tame aavi shakya na hata. 🤝,"
                    v2 = f"🌟 We missed you at our site. We understand tame busy hasso. Aa weekend par tame ane tamaro parivar amaro ready sample house jova aavi shako chho. Tamaro convenient time <b>{exec_name}</b> ({phone}) ne janavi shako chho.,"
                    v3 = "📍 for easy navigation mate site Google Location ane video link ahi chhe: 👉 🎥 Video: ... | 📖 Brochure: ... | 📍 Location: ...,"
                elif rec.campaign_type == 'site_visit_done':
                    v1 = f"Hi <b>{lead_name} ji</b>, <b>{proj_title}</b> ma tame pasand kareli unit na reference ma. ⚡,"
                    v2 = f"🌟 We would like to update you ke selected units ma booking fast chaloo chhe. Tamari preferred unit hold karva mate athva token process samajva mate <b>{exec_name}</b> ({phone}) sathe connect kari shako chho.,"
                    v3 = "📍 for unit details, floor layout ane brochure re-check karva ahi click karo: 👉 🎥 Video: ... | 📖 Brochure: ... | 📍 Location: ...,"
                else: # new_lead
                    v1 = f"Hi <b>{lead_name} ji</b>, <b>{proj_title}</b> ma tame pehla interest batavyo hato, etle tamari sathe fari connect karvanu thayu. 🙏,"
                    v2 = f"🌟 We would love to invite you to experience our *Ready Sample House / Flat*. Jo tame nava ghar ni search ma chho, toh amaro sample house ek vaar live jova jevo chhe. Amari team na <b>{exec_name}</b> ({phone}) sathe tamaro visit plan kari shako chho.,"
                    v3 = "📍 for sample house video, photos ane location ahi check kari shako chho: 👉 🎥 Video: ... | 📖 Brochure: ... | 📍 Location: ...,"
            else: # en
                if rec.campaign_type == 'contacted':
                    v1 = f"Hi <b>{lead_name}</b>, following up on our previous conversation regarding <b>{proj_title}</b>,"
                    v2 = f"🌟 We wanted to check if your property search is still active. Construction is progressing rapidly on site. For the latest pricing and unit availability, connect with <b>{exec_name}</b> ({phone}),"
                    v3 = "📍 for updated walkthrough video, brochure and location: 👉 🎥 Video: ... | 📖 Brochure: ... | 📍 Location: ...,"
                elif rec.campaign_type == 'site_visit_scheduled':
                    v1 = f"Hi <b>{lead_name}</b>, we noticed you missed your scheduled visit to <b>{proj_title}</b>,"
                    v2 = f"🌟 We missed hosting you at our site. We understand you might have been busy. We invite you and your family to reschedule your visit this weekend. Share your preferred time with <b>{exec_name}</b> ({phone}),"
                    v3 = "📍 for easy navigation, sample house video and location link: 👉 🎥 Video: ... | 📖 Brochure: ... | 📍 Location: ...,"
                elif rec.campaign_type == 'site_visit_done':
                    v1 = f"Hi <b>{lead_name}</b>, following up on your recent site visit to <b>{proj_title}</b>,"
                    v2 = f"🌟 We would like to update you that high-demand units are booking fast. To hold your preferred unit or discuss token process, please connect with <b>{exec_name}</b> ({phone}),"
                    v3 = "📍 for unit details, floor layout and brochure: 👉 🎥 Video: ... | 📖 Brochure: ... | 📍 Location: ...,"
                else:
                    v1 = f"Hi <b>{lead_name}</b>, following up on your earlier interest in <b>{proj_title}</b>,"
                    v2 = f"🌟 We would love to invite you to experience our *Ready Sample House / Flat*. If you are exploring your dream home, this weekend is the perfect time to visit. Connect with <b>{exec_name}</b> ({phone}) to plan your visit.,"
                    v3 = "📍 for project video walkthrough, brochure and exact location: 👉 🎥 Video: ... | 📖 Brochure: ... | 📍 Location: ...,"

            closing = "thanks for your time."
            rec.preview_html = Markup(f"""
                <div class="p-3 bg-light rounded border border-success font-monospace" style="white-space: pre-line; line-height: 1.6; font-size: 14px;">
                    {v1}
                    {v2}
                    {v3}
                    {closing}
                </div>
            """)

    def action_send_bulk_campaign(self):
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Only System Administrator can run bulk WhatsApp campaigns!"))

        if not self.lead_ids:
            raise UserError(_("No leads selected for this campaign!"))

        sent_count = 0
        skipped_count = 0
        failed_count = 0

        for lead in self.lead_ids:
            phone_raw = lead.phone or (lead.partner_id and lead.partner_id.phone) or ''
            digits = ''.join(filter(str.isdigit, phone_raw))
            if len(digits) < 10:
                skipped_count += 1
                continue

            try:
                success = lead.send_campaign_whatsapp(
                    campaign_type=self.campaign_type,
                    lang_choice=self.lang_choice,
                    executive_user=lead.user_id or self.env.user,
                    force_send=True
                )
                if success:
                    sent_count += 1
                    # 1.0 second pause between Meta API hits for safe pacing
                    time.sleep(1.0)
                else:
                    failed_count += 1
            except Exception as e:
                _logger.exception("Failed sending campaign to lead #%s: %s", lead.id, e)
                failed_count += 1

        summary_msg = _("🚀 Campaign Completed!\n\n✅ Successfully Delivered: %s\n⏭️ Skipped (Invalid Phone): %s\n❌ Failed: %s") % (
            sent_count, skipped_count, failed_count
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WhatsApp Campaign Execution Summary"),
                "message": summary_msg,
                "type": "success" if sent_count > 0 else "warning",
                "sticky": True
            }
        }

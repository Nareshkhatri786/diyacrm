# -*- coding: utf-8 -*-
import json
import logging
import datetime
import os
import re
from markupsafe import Markup
from odoo import http, fields, SUPERUSER_ID, _
from odoo.http import request, Response
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)

class DiyaCrmCallTrackerController(http.Controller):

    @http.route("/api/call_tracker/login", type="jsonrpc", auth="public", methods=["POST"], csrf=False)
    def call_tracker_login(self, login, password):
        try:
            env = request.env(user=SUPERUSER_ID, su=True)
            credential = {"login": login, "password": password, "type": "password"}

            uid = False
            try:
                auth_info = request.session.authenticate(env, credential)
                uid = auth_info.get("uid") if isinstance(auth_info, dict) else auth_info
            except Exception:
                try:
                    uid = env["res.users"]._login(env.cr.dbname, login, password, {"interactive": False})
                except Exception:
                    uid = False

            if not uid:
                return {"status": "error", "message": "Invalid username or password"}

            user = env["res.users"].browse(uid)
            return {
                "status": "success",
                "user_id": user.id,
                "user_name": user.name,
                "login": user.login,
                "company_id": user.company_id.id,
                "company_name": user.company_id.name,
                "session_id": request.session.sid,
            }
        except AccessDenied:
            return {"status": "error", "message": "Invalid credentials"}
        except Exception as e:
            _logger.exception("Call Tracker Login Error: %s", str(e))
            return {"status": "error", "message": str(e)}

    @http.route("/api/call_tracker/sync_call", type="jsonrpc", auth="public", methods=["POST"], csrf=False)
    def sync_call_log(self, phone_number, call_type, duration_seconds=0, start_time=None, user_id=None, company_id=None, recording_url=None):
        try:
            if not phone_number:
                return {"status": "error", "message": "Missing phone number"}

            env = request.env(user=SUPERUSER_ID, su=True)

            # 1. Identify Staff User & Primary Company
            user = False
            if user_id:
                try:
                    target_u = env["res.users"].browse(int(user_id))
                    if target_u.exists() and target_u.login != "public":
                        user = target_u
                except Exception:
                    pass

            if not user:
                user = env["res.users"].search([("share", "=", False), ("login", "!=", "admin")], limit=1)

            if company_id:
                try:
                    target_company_id = int(company_id)
                except Exception:
                    target_company_id = user.company_id.id if user else env.company.id
            else:
                target_company_id = user.company_id.id if user else env.company.id

            company = env["res.company"].browse(target_company_id)

            # 2. Extract clean 10-digit phone
            digits = re.sub(r"\D", "", str(phone_number))
            phone_10 = digits[-10:] if len(digits) >= 10 else digits

            if not phone_10:
                return {"status": "error", "message": "Invalid phone digits"}

            # Formatted time upfront
            time_display = start_time if start_time else fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 3. Search across BOTH ACTIVE & LOST LEADS
            # NOTE: In Odoo 19, crm.lead does NOT have 'mobile' field, only 'phone'
            Lead = env["crm.lead"].with_context(active_test=False)

            domain = [
                ("type", "=", "opportunity"),
                "|",
                ("phone", "ilike", phone_10),
                ("name", "ilike", phone_10)
            ]

            # First try matching via find_lead_by_phone in target company
            lead = env["crm.lead"].find_lead_by_phone(phone_number or phone_10, company_id=target_company_id, active_test=False)
            if not lead:
                # Fallback to search domain in target company
                matching_leads = Lead.search([("company_id", "=", target_company_id)] + domain, order="write_date desc")
                if not matching_leads:
                    # Search globally
                    lead = env["crm.lead"].find_lead_by_phone(phone_number or phone_10, company_id=None, active_test=False)
                    if not lead:
                        matching_leads = Lead.search(domain, order="write_date desc")
                if not lead and matching_leads:
                    real_leads = matching_leads.filtered(lambda l: not (l.name.startswith("Call:") or l.name.startswith("+91")))
                    lead = real_leads[0] if real_leads else matching_leads[0]

            if lead and lead.company_id:
                company = lead.company_id

            # Duration formatting
            dur = int(duration_seconds or 0)
            mins = dur // 60
            secs = dur % 60
            dur_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

            # Call Type Label & Outcome mapping
            call_type_lower = str(call_type).lower()
            if "out" in call_type_lower and dur > 0:
                type_label = "📞 Outgoing Call (Answered)"
                outcome = "answered"
                badge_color = "#16a34a"
                badge_bg = "#dcfce7"
            elif "out" in call_type_lower:
                type_label = "📞 Outgoing Call (No Answer / Busy)"
                outcome = "no_answer"
                badge_color = "#ea580c"
                badge_bg = "#ffedd5"
            elif "miss" in call_type_lower or "reject" in call_type_lower:
                type_label = "📲 Missed Call"
                outcome = "no_answer"
                badge_color = "#dc2626"
                badge_bg = "#fee2e2"
            else:
                type_label = "📲 Incoming Call (Answered)"
                outcome = "answered"
                badge_color = "#2563eb"
                badge_bg = "#dbeafe"

            # 4. If Lead NOT found in CRM at all:
            if not lead:
                if dur == 0 and ("miss" in call_type_lower or outcome == "no_answer"):
                    return {
                        "status": "ignored",
                        "message": f"Skipped lead creation for 0s unanswered call on unknown number {phone_number}"
                    }

                lead_vals = {
                    "name": f"Call: {phone_10}",
                    "phone": f"+91{phone_10}",
                    "type": "opportunity",
                    "user_id": user.id if user else False,
                    "company_id": target_company_id,
                }
                if "last_call_outcome" in env["crm.lead"]._fields:
                    lead_vals["last_call_outcome"] = outcome

                lead = env["crm.lead"].with_context(mail_notrack=True).create(lead_vals)

            # 5. Smart Revival: ONLY INCOMING calls by Client auto-revive Lost leads!
            lead_was_lost = not lead.active
            revival_badge = ""
            is_client_incoming = ("in" in call_type_lower or "miss" in call_type_lower)

            if lead_was_lost and is_client_incoming:
                stage_revived = env["crm.stage"].search([
                    "|", ("name", "ilike", "Contacted"), ("name", "ilike", "Qualified")
                ], limit=1)
                update_vals = {
                    "active": True,
                    "lost_reason_id": False,
                }
                if stage_revived:
                    update_vals["stage_id"] = stage_revived.id
                if "last_call_outcome" in env["crm.lead"]._fields:
                    update_vals["last_call_outcome"] = outcome

                lead.with_context(mail_notrack=True).write(update_vals)
                revival_badge = '<div style="background: #dcfce7; color: #166534; font-weight: 700; font-size: 12px; padding: 4px 10px; border-radius: 4px; margin-bottom: 8px; border: 1px solid #86efac;">🔄 RE-ENQUIRY DETECTED: Lead auto-revived from Lost to Active Pipeline!</div>'

                try:
                    call_act_type = env.ref("mail.mail_activity_data_call", raise_if_not_found=False)
                    if not call_act_type:
                        call_act_type = env["mail.activity.type"].search([("category", "=", "phonecall")], limit=1)
                    if call_act_type:
                        lead.activity_schedule(
                            activity_type_id=call_act_type.id,
                            summary="🔥 URGENT RE-ENQUIRY: Lost Client Called Back!",
                            date_deadline=fields.Date.today(),
                            user_id=lead.user_id.id if lead.user_id else (user.id if user else SUPERUSER_ID),
                            note=f"Client interaction on {time_display}. Lead auto-revived to Active pipeline. Please follow up immediately!"
                        )
                except Exception as _e:
                    _logger.warning("Activity schedule error: %s", str(_e))
            else:
                if "last_call_outcome" in env["crm.lead"]._fields:
                    lead.with_context(mail_notrack=True).write({"last_call_outcome": outcome})

            # 6. Post SINGLE Clean, Rendered HTML Card in Chatter
            lost_badge = ""
            if lead_was_lost:
                lost_badge = '<span style="background: #dcfce7; color: #166534; font-size: 10.5px; font-weight: 700; padding: 1px 7px; border-radius: 4px; margin-left: 6px;">[REVIVED RE-ENQUIRY]</span>' if is_client_incoming else '<span style="background: #fee2e2; color: #dc2626; font-size: 10.5px; font-weight: 700; padding: 1px 7px; border-radius: 4px; margin-left: 6px;">[LOST LEAD]</span>'

            audio_player_html = ""
            if not recording_url:
                recording_url = self._find_recording_on_server(phone_number, start_time)

            if recording_url:
                rel_p = recording_url.replace("https://crm.sigprop.in/recordings/", "")
                player_url = f"https://crm.sigprop.in/play_recording?file={rel_p}"
                audio_player_html = f'''
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #cbd5e1;">
                        <div style="margin-top: 4px;">
                            <a href="{player_url}" target="_blank" style="display: inline-block; padding: 7px 16px; background-color: #2563eb; color: #ffffff !important; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #1d4ed8; margin-right: 8px;">
                                <span style="color: #ffffff !important; font-weight: bold;">▶️ Play Recording</span>
                            </a>
                            <a href="{recording_url}" download style="display: inline-block; padding: 7px 12px; background-color: #ffffff; color: #334155 !important; border: 1px solid #cbd5e1; border-radius: 6px; text-decoration: none; font-size: 11.5px; font-weight: bold;">
                                <span style="color: #334155 !important; font-weight: bold;">⬇️ Download</span>
                            </a>
                        </div>
                    </div>
                '''

            chatter_body = Markup(f"""
                <div style="padding: 10px 14px; border-left: 4px solid {badge_color}; background: #f8fafc; border-radius: 6px; margin: 4px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                    {revival_badge}<div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="font-weight: 700; color: {badge_color}; font-size: 13.5px;">
                            {type_label} {lost_badge}
                        </span>
                        <span style="font-weight: 700; color: {badge_color}; background: {badge_bg}; padding: 2px 10px; border-radius: 12px; font-size: 12px;">
                            ⏱️ {dur_str}
                        </span>
                    </div>
                    <div style="font-size: 12px; color: #475569; margin-top: 5px;">
                        <b>Staff:</b> {user.name if user else "Mobile Dialer"} &nbsp;|&nbsp;
                        <b>Company:</b> {lead.company_id.name or company.name} &nbsp;|&nbsp;
                        <b>Client:</b> {lead.phone or phone_number}
                    </div>
                    {audio_player_html}
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 3px;">
                        {time_display} &bull; Auto-Synced via Diya CRM Dialer
                    </div>
                </div>
            """)

            lead.message_post(
                body=chatter_body,
                message_type="comment",
                subtype_xmlid="mail.mt_note",
                author_id=user.partner_id.id if user else False
            )

            # 7. Automated WhatsApp Follow-up in Gujarati (1 per day limit per outcome)
            try:
                lead.with_context(mail_notrack=True).send_call_followup_whatsapp(
                    call_outcome=outcome,
                    executive_user=user,
                    force_send=False,
                    lang_choice="gu"
                )
            except Exception as _we:
                _logger.warning("Automated Call WhatsApp trigger failed on lead #%s: %s", lead.id, str(_we))

            return {
                "status": "success",
                "lead_id": lead.id,
                "lead_name": lead.name,
                "company_name": lead.company_id.name or company.name,
                "duration": dur_str,
                "message": f"Successfully logged to {lead.name} ({lead.company_id.name or company.name})"
            }

        except Exception as e:
            _logger.exception("Call Sync Error: %s", str(e))
            return {"status": "error", "message": str(e)}

    @http.route("/download/dialer.apk", type="http", auth="public", methods=["GET"])
    def download_dialer_apk(self):
        apk_path = "/opt/odoo19/custom_addons/diyacrm/static/downloads/dialer.apk"
        if not os.path.exists(apk_path):
            return request.not_found("APK file is being prepared. Please check back shortly.")

        with open(apk_path, "rb") as f:
            apk_data = f.read()

        return Response(
            apk_data,
            headers=[
                ("Content-Type", "application/vnd.android.package-archive"),
                ("Content-Disposition", "attachment; filename=DiyaCRM_Dialer.apk"),
                ("Content-Length", str(len(apk_data)))
            ]
        )

    @http.route("/download/diyasync.apk", type="http", auth="public", methods=["GET"])
    def download_diyasync_apk(self):
        apk_path = "/opt/odoo19/custom_addons/diyacrm/static/downloads/diyasync.apk"
        if not os.path.exists(apk_path):
            return request.not_found("DiyaSync APK is being prepared. Please check back shortly.")

        with open(apk_path, "rb") as f:
            apk_data = f.read()

        return Response(
            apk_data,
            headers=[
                ("Content-Type", "application/vnd.android.package-archive"),
                ("Content-Disposition", "attachment; filename=DiyaSync.apk"),
                ("Content-Length", str(len(apk_data)))
            ]
        )

    @http.route(["/download/diyasync-beta.apk", "/download/beta.apk"], type="http", auth="public", methods=["GET"])
    def download_diyasync_beta_apk(self):
        apk_path = "/opt/odoo19/custom_addons/diyacrm/static/downloads/diyasync-beta.apk"
        if not os.path.exists(apk_path):
            return request.not_found("DiyaSync Beta APK is being prepared. Please check back shortly.")

        with open(apk_path, "rb") as f:
            apk_data = f.read()

        return Response(
            apk_data,
            headers=[
                ("Content-Type", "application/vnd.android.package-archive"),
                ("Content-Disposition", "attachment; filename=DiyaSync_Beta.apk"),
                ("Content-Length", str(len(apk_data)))
            ]
    @http.route(["/download/inventory_sample.csv", "/download/sample_property_units_inventory.csv"], type="http", auth="public", methods=["GET"])
    def download_inventory_sample_csv(self):
        csv_path = "/opt/odoo19/custom_addons/diyacrm/static/downloads/sample_property_units_inventory.csv"
        if not os.path.exists(csv_path):
            csv_path = os.path.join(os.path.dirname(__file__), "..", "static", "downloads", "sample_property_units_inventory.csv")
        if not os.path.exists(csv_path):
            return request.not_found("Sample CSV file not found.")

        with open(csv_path, "rb") as f:
            data = f.read()

        return Response(
            data,
            headers=[
                ("Content-Type", "text/csv; charset=utf-8"),
                ("Content-Disposition", "attachment; filename=sample_property_units_inventory.csv"),
                ("Content-Length", str(len(data)))
            ]
        )

    # ─────────────────────────────────────────────────────────────────────────
    # AUTO-DIALER FEATURE
    # ─────────────────────────────────────────────────────────────────────────

    @http.route('/api/call_tracker/get_due_queue', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def get_due_queue(self, user_id=None, company_id=None, limit=50, **kwargs):
        """
        Returns a STRICTLY ISOLATED, prioritized queue of leads for the logged-in user and company.
        Priority:
          1. Overdue Call activities for this user & company (deadline < today, not done)
          2. New uncontacted Inbound WhatsApp Leads for this user & company (no activity yet)
          3. Today's scheduled Call activities for this user & company
          4. Retry queue – leads marked no_answer in last 4 hours for this user & company
          5. Active leads with NO follow-up scheduled (to ensure no active lead is left behind)
        """
        try:
            env = request.env(user=SUPERUSER_ID, su=True)
            today = fields.Date.today()
            now = fields.Datetime.now()
            four_hrs_ago = now - datetime.timedelta(hours=4)

            # 1. Resolve logged-in user strictly
            caller_user = False
            if user_id:
                try:
                    u = env['res.users'].browse(int(user_id))
                    if u.exists() and u.login != 'public':
                        caller_user = u
                except Exception:
                    pass

            if not caller_user:
                return {'status': 'error', 'message': 'Missing or invalid user_id. Please login first.'}

            # 2. Resolve primary company strictly
            target_company_id = False
            if company_id:
                try:
                    c = env['res.company'].browse(int(company_id))
                    if c.exists():
                        target_company_id = c.id
                except Exception:
                    pass
            if not target_company_id:
                target_company_id = caller_user.company_id.id if caller_user.company_id else env.company.id

            # Base domain strictly enforcing user & company on crm.lead
            user_comp_domain = [
                ('user_id', '=', caller_user.id),
                ('company_id', '=', target_company_id),
                ('active', '=', True),
            ]

            # Helper: serialize a lead into queue item dict
            def _lead_dict(lead, priority_label, activity=None):
                last_note = ''
                if activity:
                    last_note = activity.note or activity.summary or ''
                # Fetch last chatter note
                last_msg = env['mail.message'].search([
                    ('model', '=', 'crm.lead'),
                    ('res_id', '=', lead.id),
                    ('subtype_id.internal', '=', True),
                ], order='id desc', limit=1)
                if last_msg and not last_note:
                    import html, re as _re
                    last_note = _re.sub('<[^>]+>', '', html.unescape(last_msg.body or ''))[:120]

                assigned_name = lead.user_id.name if lead.user_id else caller_user.name
                return {
                    'lead_id': lead.id,
                    'lead_name': lead.name or '',
                    'phone': lead.phone or '',
                    'company_name': lead.company_id.name or '',
                    'stage_name': lead.stage_id.name if lead.stage_id else 'New Lead',
                    'priority_label': priority_label,
                    'assigned_to': assigned_name,
                    'last_note': last_note,
                    'activity_id': activity.id if activity else False,
                    'activity_summary': activity.summary if activity else '',
                    'activity_deadline': activity.date_deadline.isoformat() if activity and activity.date_deadline else '',
                }

            queue = []
            seen_lead_ids = set()

            # ── Priority 1: Overdue Call Activities for THIS user & company ─────
            overdue_activities = env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('activity_type_id.category', '=', 'phonecall'),
                ('date_deadline', '<', today),
                ('user_id', '=', caller_user.id),
            ], order='date_deadline asc', limit=int(limit))

            for act in overdue_activities:
                lead = env['crm.lead'].browse(act.res_id)
                if not lead.exists() or not lead.active:
                    continue
                if lead.company_id.id != target_company_id or lead.user_id.id != caller_user.id:
                    continue
                if lead.id not in seen_lead_ids:
                    queue.append(_lead_dict(lead, '🔴 Overdue Follow-up', act))
                    seen_lead_ids.add(lead.id)

            # ── Priority 2: New Inbound WhatsApp Leads (no activity yet) ────────
            whatsapp_source = env['utm.source'].search([('name', 'ilike', 'WhatsApp')], limit=1)
            new_lead_stage = env['crm.stage'].search([('name', 'ilike', 'New Lead')], limit=1)
            if whatsapp_source and new_lead_stage and len(queue) < int(limit):
                new_wa_leads = env['crm.lead'].search(
                    user_comp_domain + [
                        ('source_id', '=', whatsapp_source.id),
                        ('stage_id', '=', new_lead_stage.id),
                        ('activity_ids', '=', False),
                    ],
                    order='create_date asc', limit=int(limit) - len(queue)
                )
                for lead in new_wa_leads:
                    if lead.id not in seen_lead_ids:
                        queue.append(_lead_dict(lead, '🟡 New WhatsApp Enquiry (First Call!)', None))
                        seen_lead_ids.add(lead.id)

            # ── Priority 3: Today's Scheduled Call Activities ─────────────────
            if len(queue) < int(limit):
                today_activities = env['mail.activity'].search([
                    ('res_model', '=', 'crm.lead'),
                    ('activity_type_id.category', '=', 'phonecall'),
                    ('date_deadline', '=', today),
                    ('user_id', '=', caller_user.id),
                ], order='date_deadline asc', limit=int(limit) - len(queue))

                for act in today_activities:
                    lead = env['crm.lead'].browse(act.res_id)
                    if not lead.exists() or not lead.active:
                        continue
                    if lead.company_id.id != target_company_id or lead.user_id.id != caller_user.id:
                        continue
                    if lead.id not in seen_lead_ids:
                        queue.append(_lead_dict(lead, '🔵 Today\'s Follow-up', act))
                        seen_lead_ids.add(lead.id)

            # ── Priority 4: Retry – leads with 'no_answer' in last 4 hours ───
            if len(queue) < int(limit) and 'last_call_outcome' in env['crm.lead']._fields:
                retry_leads = env['crm.lead'].search(
                    user_comp_domain + [
                        ('last_call_outcome', '=', 'no_answer'),
                        ('write_date', '>=', four_hrs_ago.strftime('%Y-%m-%d %H:%M:%S')),
                    ],
                    order='write_date asc', limit=int(limit) - len(queue)
                )
                for lead in retry_leads:
                    if lead.id not in seen_lead_ids:
                        queue.append(_lead_dict(lead, '🟠 Retry – No Answer Earlier', None))
                        seen_lead_ids.add(lead.id)

            # ── Priority 5: Active Leads with NO Follow-up Scheduled ─────────
            # When all due calls are done, pull unattended active leads
            if len(queue) < int(limit):
                no_act_leads = env['crm.lead'].search(
                    user_comp_domain + [
                        ('activity_ids', '=', False),
                    ],
                    order='write_date desc', limit=int(limit) - len(queue)
                )
                for lead in no_act_leads:
                    if lead.id not in seen_lead_ids:
                        queue.append(_lead_dict(lead, '⚪ Active Lead (No Follow-up Scheduled)', None))
                        seen_lead_ids.add(lead.id)

            return {
                'status': 'success',
                'user_id': caller_user.id,
                'user_name': caller_user.name,
                'company_id': target_company_id,
                'count': len(queue),
                'queue': queue,
            }

        except Exception as e:
            _logger.exception("get_due_queue error: %s", str(e))
            return {'status': 'error', 'message': str(e)}

    @http.route('/api/call_tracker/submit_call_wrapup', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def submit_call_wrapup(self, lead_id, outcome, notes='', next_followup_days=1,
                           next_followup_date=None, next_followup_type='call',
                           activity_id=None, user_id=None, duration_seconds=0,
                           phone_number=None, **kwargs):
        """
        One-shot post-call wrap-up API:
          1. Marks existing activity as DONE with feedback
          2. Schedules next follow-up activity
          3. Auto-updates lead stage based on outcome
          4. Posts a rich chatter note
          5. Triggers WhatsApp follow-up (if applicable)
        """
        try:
            env = request.env(user=SUPERUSER_ID, su=True)
            today = fields.Date.today()
            now = fields.Datetime.now()

            lead = env['crm.lead'].browse(int(lead_id))
            if not lead.exists():
                return {'status': 'error', 'message': f'Lead #{lead_id} not found'}

            # Resolve caller user
            caller_user = env.ref('base.user_admin')
            if user_id:
                try:
                    u = env['res.users'].browse(int(user_id))
                    if u.exists() and u.login != 'public':
                        caller_user = u
                except Exception:
                    pass

            # Duration formatting
            dur = int(duration_seconds or 0)
            mins, secs = dur // 60, dur % 60
            dur_str = f"{mins}m {secs}s" if mins > 0 else (f"{secs}s" if secs > 0 else "—")

            # Outcome mapping
            outcome_map = {
                'interested': {'label': '🟢 Interested', 'color': '#16a34a', 'bg': '#dcfce7'},
                'callback':   {'label': '🟡 Busy / Callback Later', 'color': '#ca8a04', 'bg': '#fef9c3'},
                'no_answer':  {'label': '🔴 No Answer', 'color': '#dc2626', 'bg': '#fee2e2'},
                'not_interested': {'label': '⚫ Not Interested', 'color': '#64748b', 'bg': '#f1f5f9'},
                'site_visit': {'label': '🏠 Site Visit Scheduled', 'color': '#2563eb', 'bg': '#dbeafe'},
                'revisit':    {'label': '🔁 Will Revisit / Think', 'color': '#7c3aed', 'bg': '#ede9fe'},
            }
            oc = outcome_map.get(str(outcome).lower(), outcome_map['callback'])

            # ── Step 1: Mark existing activity as DONE ─────────────────────
            done_act = False
            if activity_id:
                try:
                    act = env['mail.activity'].browse(int(activity_id))
                    if act.exists():
                        done_act = act
                except Exception:
                    pass
            if not done_act:
                done_act = env['mail.activity'].search([
                    ('res_model', '=', 'crm.lead'),
                    ('res_id', '=', lead.id),
                    ('activity_type_id.category', '=', 'phonecall'),
                ], order='id asc', limit=1)

            feedback_text = f"Call Outcome: {oc['label']}\nDuration: {dur_str}\n"
            if notes:
                feedback_text += f"Notes: {notes}"

            if done_act:
                try:
                    done_act._action_done(feedback=feedback_text)
                except Exception:
                    try:
                        done_act.action_done_schedule_next(feedback=feedback_text)
                    except Exception:
                        done_act.write({'active': False})

            # ── Step 2: Auto Stage Update based on Outcome ─────────────────
            stage_map = {
                'interested':     [['Contacted', 'Qualified']],
                'callback':       [['Contacted', 'New Lead']],
                'site_visit':     [['Site Visit Scheduled', 'Site Visit']],
                'revisit':        [['Contacted']],
                'no_answer':      None,
                'not_interested': None,
            }
            stage_keywords = stage_map.get(str(outcome).lower())
            if stage_keywords:
                for kw_list in stage_keywords:
                    for kw in kw_list:
                        new_stage = env['crm.stage'].search([('name', 'ilike', kw)], limit=1)
                        if new_stage:
                            # Only advance stage, never go back
                            if not lead.stage_id or (lead.stage_id.sequence or 0) < (new_stage.sequence or 0):
                                lead.with_context(mail_notrack=True).write({'stage_id': new_stage.id})
                            break
                    else:
                        continue
                    break

            # Map our outcome labels to the crm.lead field's valid selection values
            # Valid: 'answered', 'no_answer', 'busy', 'switched_off'
            OUTCOME_TO_FIELD = {
                'interested':     'answered',
                'callback':       'busy',
                'no_answer':      'no_answer',
                'not_interested': 'no_answer',
                'site_visit':     'answered',
                'revisit':        'busy',
            }
            if 'last_call_outcome' in env['crm.lead']._fields:
                field_val = OUTCOME_TO_FIELD.get(str(outcome).lower(), 'no_answer')
                lead.with_context(mail_notrack=True).write({'last_call_outcome': field_val})

            # ── Step 3: Schedule Next Follow-up Activity ────────────────────
            next_act_id = False
            schedule_next = str(outcome).lower() not in ('not_interested',)
            if schedule_next:
                # Determine next follow-up date
                if next_followup_date:
                    try:
                        import datetime as _dt
                        next_date = _dt.date.fromisoformat(str(next_followup_date))
                    except Exception:
                        next_date = today + datetime.timedelta(days=int(next_followup_days or 1))
                else:
                    days_map = {
                        'interested':     1,
                        'callback':       0,   # Same day
                        'no_answer':      0,   # Retry same day (afternoon)
                        'site_visit':     3,
                        'revisit':        2,
                    }
                    days_delta = days_map.get(str(outcome).lower(), int(next_followup_days or 1))
                    next_date = today + datetime.timedelta(days=days_delta)

                # Determine activity type
                if str(outcome).lower() == 'site_visit' or str(next_followup_type).lower() in ('visit', 'meeting', 'site_visit'):
                    act_type = env['mail.activity.type'].search([
                        '|', ('name', 'ilike', 'Site Visit'), ('name', 'ilike', 'Meeting')
                    ], limit=1)
                    act_summary = "🏠 Site Visit – Confirm & Prepare"
                else:
                    act_type = env.ref('mail.mail_activity_data_call', raise_if_not_found=False)
                    if not act_type:
                        act_type = env['mail.activity.type'].search([('category', '=', 'phonecall')], limit=1)
                    outcome_summary_map = {
                        'interested':  "🔥 Follow-up Call – High Priority Lead",
                        'callback':    "📞 Callback Requested",
                        'no_answer':   "📞 Retry Call – Did Not Answer",
                        'revisit':     "📞 Follow-up – Will Think About It",
                        'site_visit':  "📞 Post Site-Visit Follow-up",
                    }
                    act_summary = outcome_summary_map.get(str(outcome).lower(), "📞 Follow-up Call")

                if act_type:
                    scheduled_act = lead.activity_schedule(
                        activity_type_id=act_type.id,
                        summary=act_summary,
                        date_deadline=next_date,
                        user_id=caller_user.id,
                        note=notes or f"Post-call follow-up after: {oc['label']}"
                    )
                    next_act_id = scheduled_act.id if scheduled_act else False

            # ── Step 4: Post rich chatter note ─────────────────────────────
            notes_html = f'<div style="margin-top:6px;background:#f8fafc;padding:6px 10px;border-radius:4px;font-size:12px;color:#334155;white-space:pre-wrap;">{notes}</div>' if notes else ''
            next_followup_html = ''
            if next_act_id:
                nact = env['mail.activity'].browse(next_act_id)
                next_followup_html = f'''
                <div style="margin-top:8px;padding:6px 10px;border-radius:4px;background:#eff6ff;border:1px solid #bfdbfe;font-size:11.5px;color:#1e40af;">
                    📅 <b>Next Follow-up Scheduled:</b> {nact.date_deadline.strftime("%d %b %Y") if nact.date_deadline else "Today"} — {nact.summary or "Call"}
                </div>'''

            chatter_html = f'''
<div style="padding:10px 14px;border-left:4px solid {oc["color"]};background:#f8fafc;border-radius:6px;margin:4px 0;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
    <div style="display:flex;align-items:center;justify-content:space-between;">
        <span style="font-weight:700;color:{oc["color"]};font-size:13.5px;">
            {oc["label"]} &nbsp;
            <span style="font-size:11px;font-weight:600;background:{oc["bg"]};color:{oc["color"]};padding:2px 8px;border-radius:10px;">
                Auto-Dialer Wrap-up
            </span>
        </span>
        <span style="font-weight:700;color:{oc["color"]};background:{oc["bg"]};padding:2px 10px;border-radius:12px;font-size:12px;">
            ⏱️ {dur_str}
        </span>
    </div>
    <div style="font-size:12px;color:#475569;margin-top:5px;">
        <b>Executive:</b> {caller_user.name} &nbsp;|&nbsp;
        <b>Project:</b> {lead.company_id.name or ""} &nbsp;|&nbsp;
        <b>Client:</b> {lead.phone or phone_number or ""}
    </div>
    {notes_html}
    {next_followup_html}
    <div style="font-size:11px;color:#94a3b8;margin-top:4px;">
        {now.strftime("%d-%b-%Y %I:%M %p")} &bull; Auto-Synced via Diya CRM Auto-Dialer
    </div>
</div>'''

            lead.message_post(
                body=Markup(chatter_html),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
                author_id=caller_user.partner_id.id if caller_user else False,
            )

            # ── Step 5: WhatsApp follow-up trigger in Gujarati (Always send) ───
            wa_sent = False
            try:
                # 2 Options: Connected (answered) or Not Answered (no_answer)
                is_connected_outcome = str(outcome).lower() in ('interested', 'site_visit', 'revisit', 'callback', 'answered', 'connected')
                wa_outcome = "answered" if is_connected_outcome else "no_answer"

                wa_sent = lead.with_context(mail_notrack=True).send_call_followup_whatsapp(
                    call_outcome=wa_outcome,
                    executive_user=caller_user,
                    force_send=True,
                    lang_choice='gu'
                )
                _logger.info("Auto-dialer WA trigger: lead #%s, outcome=%s -> wa_outcome=%s, sent=%s", lead.id, outcome, wa_outcome, wa_sent)
            except Exception as _we:
                _logger.warning("Auto-dialer WA trigger error: %s", str(_we))

            return {
                'status': 'success',
                'lead_id': lead.id,
                'lead_name': lead.name,
                'stage_name': lead.stage_id.name if lead.stage_id else '',
                'next_activity_id': next_act_id,
                'whatsapp_sent': bool(wa_sent),
                'message': f"Wrap-up saved for {lead.name}",
            }

        except Exception as e:
            _logger.exception("submit_call_wrapup error: %s", str(e))
            return {'status': 'error', 'message': str(e)}

    @http.route('/auto-dialer', type='http', auth='public', methods=['GET'], csrf=False)
    def auto_dialer_page(self, **kwargs):
        """
        Standalone Auto-Dialer Web Interface.
        Works on both Desktop (CRM Web) and Mobile Browser.
        """
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>🚀 Diya CRM Auto-Dialer</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
body{background:#0f172a;min-height:100vh;display:flex;flex-direction:column}
.topbar{background:#1e293b;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #334155}
.topbar h1{color:#fff;font-size:16px;font-weight:700}
.topbar .meta{color:#94a3b8;font-size:12px}
#loginPanel{max-width:360px;margin:60px auto 0;background:#1e293b;border-radius:12px;padding:28px;border:1px solid #334155}
#loginPanel h2{color:#fff;font-size:18px;margin-bottom:20px;text-align:center}
.inp{width:100%;padding:10px 12px;background:#0f172a;border:1px solid #475569;border-radius:8px;color:#fff;font-size:14px;margin-bottom:12px;outline:none}
.inp:focus{border-color:#3b82f6}
.btn{width:100%;padding:12px;border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;transition:opacity .2s}
.btn-primary{background:#3b82f6;color:#fff}
.btn-primary:hover{opacity:.88}
.btn-success{background:#16a34a;color:#fff}
.btn-warn{background:#ca8a04;color:#fff}
.btn-danger{background:#dc2626;color:#fff}
.btn-secondary{background:#475569;color:#fff}
.btn-violet{background:#7c3aed;color:#fff}
.btn-blue{background:#2563eb;color:#fff}
#dialerPanel{display:none;flex:1;flex-direction:column}
.queue-header{background:#1e293b;padding:12px 16px;display:flex;align-items:center;gap:10px;border-bottom:1px solid #334155}
.badge{background:#3b82f6;color:#fff;border-radius:20px;padding:2px 10px;font-size:12px;font-weight:700}
.queue-list{flex:1;overflow-y:auto;padding:12px}
.queue-item{background:#1e293b;border-radius:10px;padding:12px 14px;margin-bottom:8px;border:1px solid #334155;cursor:pointer;transition:border-color .15s}
.queue-item:hover,.queue-item.active{border-color:#3b82f6}
.queue-item .prio{font-size:12px;font-weight:700;margin-bottom:4px}
.queue-item .name{color:#fff;font-size:14px;font-weight:700}
.queue-item .sub{color:#94a3b8;font-size:12px;margin-top:2px}
#callPanel{display:none;position:fixed;inset:0;background:#0f172a;flex-direction:column;z-index:100}
.call-header{background:#1e293b;padding:16px;border-bottom:1px solid #334155}
.call-name{color:#fff;font-size:20px;font-weight:700}
.call-sub{color:#94a3b8;font-size:13px;margin-top:2px}
.call-phone{color:#3b82f6;font-size:28px;font-weight:700;text-align:center;margin:20px 0 4px}
.call-stage{color:#94a3b8;font-size:13px;text-align:center;margin-bottom:8px}
.call-note-prev{background:#1e293b;border-radius:8px;margin:0 16px;padding:10px 12px;color:#cbd5e1;font-size:12px;min-height:36px}
.call-btn-row{display:flex;gap:10px;padding:16px;justify-content:center}
.call-btn-row .btn{width:auto;flex:1;padding:14px 0;font-size:14px}
.timer{text-align:center;color:#4ade80;font-size:24px;font-weight:700;font-variant-numeric:tabular-nums;margin:10px 0}
#wrapupPanel{display:none;position:fixed;inset:0;background:#0f172a;flex-direction:column;overflow-y:auto;z-index:200}
.wrapup-inner{max-width:480px;margin:0 auto;padding:20px}
.wrapup-inner h2{color:#fff;font-size:18px;font-weight:700;margin-bottom:16px}
.section-label{color:#94a3b8;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;margin-top:16px}
.outcome-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:4px}
.outcome-btn{background:#1e293b;border:2px solid #334155;border-radius:8px;padding:12px 8px;text-align:center;cursor:pointer;color:#e2e8f0;font-size:13px;font-weight:600;transition:all .15s}
.outcome-btn.sel{border-color:#3b82f6;background:#1d3461;color:#93c5fd}
.follow-chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:4px}
.chip{background:#1e293b;border:2px solid #334155;border-radius:20px;padding:8px 14px;font-size:12px;font-weight:600;cursor:pointer;color:#cbd5e1;white-space:nowrap}
.chip.sel{border-color:#3b82f6;background:#1d3461;color:#93c5fd}
textarea.inp{resize:vertical;min-height:72px}
.countdown-bar{background:#1e293b;border-radius:8px;padding:14px;text-align:center;margin-bottom:14px}
.countdown-num{color:#4ade80;font-size:36px;font-weight:700;font-variant-numeric:tabular-nums}
.countdown-sub{color:#94a3b8;font-size:12px;margin-top:2px}
.skip-link{color:#64748b;text-align:center;font-size:12px;cursor:pointer;margin-top:8px;text-decoration:underline}
.toast{position:fixed;top:16px;left:50%;transform:translateX(-50%);background:#16a34a;color:#fff;padding:10px 20px;border-radius:8px;font-size:13px;font-weight:600;z-index:999;opacity:0;transition:opacity .3s}
.toast.show{opacity:1}
</style>
</head>
<body>

<!-- TOP BAR -->
<div class="topbar">
  <h1>🚀 Diya CRM Auto-Dialer</h1>
  <div class="meta" id="userMeta"></div>
</div>

<!-- LOGIN PANEL -->
<div id="loginPanel">
  <h2>🔐 Login to Start Calling</h2>
  <input class="inp" id="loginUser" type="text" placeholder="Username / Email" autocomplete="username">
  <input class="inp" id="loginPass" type="password" placeholder="Password" autocomplete="current-password">
  <button class="btn btn-primary" onclick="doLogin()">Login & Load My Queue</button>
  <div id="loginError" style="color:#f87171;font-size:12px;margin-top:10px;text-align:center"></div>
</div>

<!-- DIALER PANEL (Queue List) -->
<div id="dialerPanel">
  <div class="queue-header">
    <div>
      <div style="color:#fff;font-weight:700;font-size:14px">📋 Today's Call Queue</div>
      <div class="meta" id="queueMeta"></div>
    </div>
    <span class="badge" id="queueCount">0</span>
    <button class="btn btn-success" style="width:auto;padding:8px 16px;margin-left:auto;font-size:13px" onclick="startAutoDialer()">▶️ Start Auto-Dialer</button>
    <button class="btn btn-secondary" style="width:auto;padding:8px 12px;font-size:13px" onclick="refreshQueue()" title="Refresh Queue">🔄</button>
  </div>
  <div class="queue-list" id="queueList"></div>
</div>

<!-- ACTIVE CALL PANEL -->
<div id="callPanel">
  <div class="call-header">
    <div style="display:flex;align-items:center;justify-content:space-between">
      <div>
        <div class="call-name" id="callLeadName"></div>
        <div class="call-sub" id="callCompany"></div>
      </div>
      <div style="color:#64748b;font-size:12px" id="callProgress"></div>
    </div>
  </div>
  <div class="call-phone" id="callPhone"></div>
  <div class="call-stage" id="callStage"></div>
  <div style="padding:0 16px 8px;color:#94a3b8;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px">Last Note</div>
  <div class="call-note-prev" id="callLastNote">—</div>
  <div class="timer" id="callTimer">00:00</div>
  <div class="call-btn-row">
    <button class="btn btn-success" id="callBtn" onclick="handleCallBtn()">📞 Dial Now</button>
    <button class="btn btn-secondary" onclick="skipLead()">⏭ Skip</button>
    <button class="btn btn-danger" onclick="stopAutoDialer()">⏹ Stop</button>
  </div>
  <div style="padding:0 16px 8px">
    <div style="color:#94a3b8;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Priority</div>
    <div id="callPriority" style="font-size:13px;color:#e2e8f0"></div>
  </div>
</div>

<!-- WRAP-UP PANEL -->
<div id="wrapupPanel">
  <div class="wrapup-inner">
    <h2>📋 Call Wrap-up</h2>
    <div style="background:#1e293b;border-radius:8px;padding:10px 12px;margin-bottom:4px">
      <div style="color:#fff;font-weight:700" id="wuLeadName"></div>
      <div style="color:#94a3b8;font-size:12px" id="wuPhone"></div>
    </div>

    <div class="section-label">Call Outcome</div>
    <div class="outcome-grid">
      <div class="outcome-btn" onclick="selectOutcome('interested')">🟢 Interested</div>
      <div class="outcome-btn" onclick="selectOutcome('callback')">🟡 Callback Later</div>
      <div class="outcome-btn" onclick="selectOutcome('no_answer')">🔴 No Answer</div>
      <div class="outcome-btn" onclick="selectOutcome('revisit')">🔁 Will Think</div>
      <div class="outcome-btn" onclick="selectOutcome('site_visit')">🏠 Site Visit Booked</div>
      <div class="outcome-btn" onclick="selectOutcome('not_interested')">⚫ Not Interested</div>
    </div>

    <div class="section-label" id="followupLabel">Next Follow-up</div>
    <div class="follow-chips" id="followChips">
      <div class="chip" onclick="selectChip(this,0)">📞 Aaj Shaam</div>
      <div class="chip" onclick="selectChip(this,1)">📅 Kal Subah</div>
      <div class="chip" onclick="selectChip(this,2)">2 Din Baad</div>
      <div class="chip" onclick="selectChip(this,3)">Agle Hafte</div>
      <div class="chip sel" onclick="selectChip(this,-1)">📆 Custom</div>
    </div>
    <input class="inp" type="date" id="customDate" style="margin-bottom:0">

    <div class="section-label">Notes (Voice ya Type karo)</div>
    <textarea class="inp" id="wuNotes" placeholder="Client ne kya kaha? Budget? BHK? Location preference? (Bolkar bhi bol sakte ho)..."></textarea>
    <button class="btn btn-secondary" id="voiceBtn" onclick="toggleVoice()" style="margin-bottom:12px;padding:10px">🎤 Voice Note Start</button>

    <div class="countdown-bar" id="countdownBar" style="display:none">
      <div class="countdown-num" id="countdownNum">5</div>
      <div class="countdown-sub">seconds me next call start hoga...</div>
      <div class="skip-link" onclick="cancelCountdown()">⏸ Pause / Cancel Countdown</div>
    </div>

    <button class="btn btn-primary" onclick="submitWrapup()" style="padding:14px;font-size:15px;margin-bottom:10px">✅ Save & Next Lead</button>
    <button class="btn btn-secondary" onclick="submitWrapup(true)" style="padding:12px;font-size:14px">💾 Save & Pause Dialer</button>
    <button class="btn btn-danger" style="margin-top:8px;padding:10px;font-size:13px" onclick="stopAutoDialer()">⏹ Stop Auto-Dialer</button>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const BASE = window.location.origin;
let SESSION = {};
let QUEUE = [];
let QUEUE_IDX = 0;
let CURRENT_LEAD = null;
let CALL_TIMER = null;
let CALL_SECS = 0;
let CALL_STARTED = false;
let SELECTED_OUTCOME = null;
let SELECTED_DAYS = 1;
let COUNTDOWN_TIMER = null;
let recognition = null;

function showToast(msg, color='#16a34a'){
  const t=document.getElementById('toast');
  t.style.background=color;t.textContent=msg;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),3000);
}

// ── LOGIN ────────────────────────────────────────────────────────────────
async function doLogin(){
  const login=document.getElementById('loginUser').value.trim();
  const pass=document.getElementById('loginPass').value;
  document.getElementById('loginError').textContent='';
  if(!login||!pass){document.getElementById('loginError').textContent='Login aur Password dono bharein.';return;}
  const res=await rpc('/api/call_tracker/login',{login,password:pass});
  if(res&&res.status==='success'){
    SESSION=res;
    document.getElementById('userMeta').textContent=res.user_name+' · '+res.company_name;
    document.getElementById('loginPanel').style.display='none';
    document.getElementById('dialerPanel').style.display='flex';
    document.getElementById('dialerPanel').style.flexDirection='column';
    await refreshQueue();
  } else {
    document.getElementById('loginError').textContent=res?.message||'Login failed. Please check credentials.';
  }
}

// ── QUEUE ────────────────────────────────────────────────────────────────
async function refreshQueue(){
  document.getElementById('queueCount').textContent='...';
  const res=await rpc('/api/call_tracker/get_due_queue',{
    user_id:SESSION.user_id,
    company_id:SESSION.company_id,
    limit:60
  });
  if(res&&res.status==='success'){
    QUEUE=res.queue||[];
    QUEUE_IDX=0;
    document.getElementById('queueCount').textContent=QUEUE.length;
    document.getElementById('queueMeta').textContent='Kul '+QUEUE.length+' leads queue mein hai';
    renderQueueList();
  }
}

function renderQueueList(){
  const el=document.getElementById('queueList');
  if(!QUEUE.length){
    el.innerHTML='<div style="text-align:center;color:#64748b;padding:40px 0">🎉 Aaj ke saare due calls complete ho gaye!</div>';
    return;
  }
  el.innerHTML=QUEUE.map((l,i)=>`
    <div class="queue-item ${i===QUEUE_IDX?'active':''}" onclick="selectLead(${i})">
      <div class="prio" style="color:${prioColor(l.priority_label)}">${l.priority_label}</div>
      <div class="name">${l.lead_name||l.phone}</div>
      <div class="sub">${l.phone} · ${l.company_name} · <span style="color:#cbd5e1">${l.stage_name}</span></div>
      ${l.last_note?`<div class="sub" style="margin-top:4px;font-style:italic">"${l.last_note.substring(0,80)}..."</div>`:''}
    </div>`).join('');
}

function prioColor(p){
  if(p.includes('Overdue'))return'#f87171';
  if(p.includes('WhatsApp'))return'#fbbf24';
  if(p.includes('Today'))return'#60a5fa';
  if(p.includes('Retry'))return'#fb923c';
  return'#94a3b8';
}

function selectLead(idx){
  QUEUE_IDX=idx;
  renderQueueList();
  CURRENT_LEAD=QUEUE[idx];
}

// ── AUTO-DIALER ──────────────────────────────────────────────────────────
function startAutoDialer(){
  if(!QUEUE.length){showToast('Queue empty hai! Refresh karo.','#dc2626');return;}
  QUEUE_IDX=0;
  loadCurrentLead();
}

function loadCurrentLead(){
  if(QUEUE_IDX>=QUEUE.length){
    showCallPanel(false);
    showToast('🎉 Saare '+QUEUE.length+' calls complete!');
    document.getElementById('dialerPanel').style.display='flex';
    return;
  }
  CURRENT_LEAD=QUEUE[QUEUE_IDX];
  CALL_STARTED=false;
  CALL_SECS=0;
  clearInterval(CALL_TIMER);

  showCallPanel(true);
  document.getElementById('callLeadName').textContent=CURRENT_LEAD.lead_name||CURRENT_LEAD.phone;
  document.getElementById('callCompany').textContent=CURRENT_LEAD.company_name+' · '+CURRENT_LEAD.assigned_to;
  document.getElementById('callPhone').textContent=CURRENT_LEAD.phone;
  document.getElementById('callStage').textContent='Stage: '+CURRENT_LEAD.stage_name;
  document.getElementById('callLastNote').textContent=CURRENT_LEAD.last_note||'—';
  document.getElementById('callTimer').textContent='00:00';
  document.getElementById('callProgress').textContent=(QUEUE_IDX+1)+' / '+QUEUE.length;
  document.getElementById('callPriority').textContent=CURRENT_LEAD.priority_label;
  document.getElementById('callBtn').textContent='📞 Dial Now';
  document.getElementById('callBtn').style.background='#16a34a';
}

function showCallPanel(show){
  document.getElementById('callPanel').style.display=show?'flex':'none';
  document.getElementById('wrapupPanel').style.display='none';
  if(show){document.getElementById('callPanel').style.flexDirection='column';}
}

function handleCallBtn(){
  if(!CALL_STARTED){
    // Initiate call via tel: link (mobile SIM) or Odoo click-to-call
    const phone=CURRENT_LEAD.phone.replace(/\\D/g,'');
    window.location.href='tel:+91'+phone;
    CALL_STARTED=true;
    document.getElementById('callBtn').textContent='✅ Call Ho Rahi Hai – Wrapup Karo';
    document.getElementById('callBtn').style.background='#2563eb';
    // Start timer
    CALL_SECS=0;
    CALL_TIMER=setInterval(()=>{
      CALL_SECS++;
      const m=Math.floor(CALL_SECS/60).toString().padStart(2,'0');
      const s=(CALL_SECS%60).toString().padStart(2,'0');
      document.getElementById('callTimer').textContent=m+':'+s;
    },1000);
  } else {
    clearInterval(CALL_TIMER);
    showWrapup();
  }
}

function skipLead(){
  clearInterval(CALL_TIMER);
  QUEUE_IDX++;
  loadCurrentLead();
}

function stopAutoDialer(){
  clearInterval(CALL_TIMER);
  cancelCountdown();
  showCallPanel(false);
  document.getElementById('wrapupPanel').style.display='none';
  document.getElementById('dialerPanel').style.display='flex';
  showToast('Auto-Dialer paused.','#ca8a04');
}

// ── WRAP-UP ──────────────────────────────────────────────────────────────
function showWrapup(){
  document.getElementById('callPanel').style.display='none';
  const wu=document.getElementById('wrapupPanel');
  wu.style.display='flex';
  wu.style.flexDirection='column';
  document.getElementById('wuLeadName').textContent=CURRENT_LEAD.lead_name||CURRENT_LEAD.phone;
  document.getElementById('wuPhone').textContent=CURRENT_LEAD.phone+' · '+CURRENT_LEAD.company_name;
  document.getElementById('wuNotes').value='';
  SELECTED_OUTCOME=null;
  SELECTED_DAYS=1;
  document.querySelectorAll('.outcome-btn').forEach(b=>b.classList.remove('sel'));
  // Default chip: Kal Subah
  document.querySelectorAll('.chip').forEach((c,i)=>{c.classList.remove('sel');if(i===1)c.classList.add('sel');});
  SELECTED_DAYS=1;
  const tomorrow=new Date();tomorrow.setDate(tomorrow.getDate()+1);
  document.getElementById('customDate').value=tomorrow.toISOString().split('T')[0];
  document.getElementById('countdownBar').style.display='none';
}

function selectOutcome(val){
  SELECTED_OUTCOME=val;
  document.querySelectorAll('.outcome-btn').forEach(b=>b.classList.remove('sel'));
  event.target.classList.add('sel');
  // Auto-chips based on outcome
  const chipMap={interested:1,callback:0,no_answer:0,site_visit:3,revisit:2,not_interested:-1};
  const days=chipMap[val]??1;
  SELECTED_DAYS=days;
  const chips=document.querySelectorAll('.chip');
  chips.forEach(c=>c.classList.remove('sel'));
  if(val==='not_interested'){
    document.getElementById('followupLabel').style.opacity='.3';
    document.getElementById('followChips').style.opacity='.3';
  } else {
    document.getElementById('followupLabel').style.opacity='1';
    document.getElementById('followChips').style.opacity='1';
    if(days===0)chips[0]?.classList.add('sel');
    else if(days===1)chips[1]?.classList.add('sel');
    else if(days===2)chips[2]?.classList.add('sel');
    else if(days>=3)chips[3]?.classList.add('sel');
  }
}

function selectChip(el,days){
  document.querySelectorAll('.chip').forEach(c=>c.classList.remove('sel'));
  el.classList.add('sel');
  if(days===-1){
    SELECTED_DAYS=-1; // custom date
  } else {
    SELECTED_DAYS=days;
    const d=new Date();d.setDate(d.getDate()+days);
    document.getElementById('customDate').value=d.toISOString().split('T')[0];
  }
}

function toggleVoice(){
  const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SpeechRecognition){showToast('Voice recognition supported nahi hai is browser mein.','#dc2626');return;}
  if(recognition){recognition.stop();recognition=null;document.getElementById('voiceBtn').textContent='🎤 Voice Note Start';return;}
  recognition=new SpeechRecognition();
  recognition.lang='hi-IN';
  recognition.continuous=true;
  recognition.interimResults=false;
  recognition.onresult=e=>{
    const t=Array.from(e.results).map(r=>r[0].transcript).join(' ');
    document.getElementById('wuNotes').value+=' '+t;
  };
  recognition.onend=()=>{recognition=null;document.getElementById('voiceBtn').textContent='🎤 Voice Note Start';};
  recognition.start();
  document.getElementById('voiceBtn').textContent='🛑 Voice Note Stop';
}

async function submitWrapup(pause=false){
  if(!SELECTED_OUTCOME){showToast('Pehle Call Outcome chunein!','#dc2626');return;}
  if(recognition){recognition.stop();recognition=null;}

  const customDateVal=document.getElementById('customDate').value;
  const notes=document.getElementById('wuNotes').value.trim();

  const payload={
    lead_id:CURRENT_LEAD.lead_id,
    outcome:SELECTED_OUTCOME,
    notes,
    next_followup_days:SELECTED_DAYS===-1?1:SELECTED_DAYS,
    next_followup_date:SELECTED_DAYS===-1?customDateVal:'',
    activity_id:CURRENT_LEAD.activity_id||false,
    user_id:SESSION.user_id,
    duration_seconds:CALL_SECS,
    phone_number:CURRENT_LEAD.phone,
  };

  const res=await rpc('/api/call_tracker/submit_call_wrapup',payload);
  if(res&&res.status==='success'){
    showToast('✅ '+res.lead_name+' – Saved!');
    QUEUE_IDX++;

    if(pause||QUEUE_IDX>=QUEUE.length){
      document.getElementById('wrapupPanel').style.display='none';
      document.getElementById('dialerPanel').style.display='flex';
      renderQueueList();
      if(QUEUE_IDX>=QUEUE.length)showToast('🎉 Sabhi leads complete ho gayi!');
      return;
    }

    // Countdown to next call
    document.getElementById('countdownBar').style.display='block';
    let count=5;
    document.getElementById('countdownNum').textContent=count;
    COUNTDOWN_TIMER=setInterval(()=>{
      count--;
      document.getElementById('countdownNum').textContent=count;
      if(count<=0){cancelCountdown();loadCurrentLead();}
    },1000);
  } else {
    showToast('Error: '+(res?.message||'Unknown error'),'#dc2626');
  }
}

function cancelCountdown(){
  clearInterval(COUNTDOWN_TIMER);
  COUNTDOWN_TIMER=null;
  document.getElementById('countdownBar').style.display='none';
}

// ── JSON-RPC HELPER ──────────────────────────────────────────────────────
async function rpc(url,params){
  try{
    const r=await fetch(BASE+url,{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      credentials:'include',
      body:JSON.stringify({jsonrpc:'2.0',method:'call',id:Date.now(),params})
    });
    const j=await r.json();
    return j.result||j.error?.data||j;
  }catch(e){return{status:'error',message:e.message};}
}

// Enter key on login
document.getElementById('loginPass').addEventListener('keydown',e=>{if(e.key==='Enter')doLogin();});
document.getElementById('loginUser').addEventListener('keydown',e=>{if(e.key==='Enter')document.getElementById('loginPass').focus();});
</script>
</body>
</html>"""
        return Response(html_content, content_type='text/html; charset=utf-8', status=200)

    @http.route('/api/call_tracker/upload_recording', type='http', auth='public',
                methods=['POST'], csrf=False)
    def upload_recording(self, **kwargs):
        import os, time, re, json
        try:
            su_id = getattr(odoo, 'SUPERUSER_ID', 1)
            try:
                env = request.env(user=su_id, su=True)
            except Exception:
                db_name = getattr(request, 'db', None) or 'diyacrm'
                registry = Registry(db_name)
                cr = registry.cursor()
                env = odoo.api.Environment(cr, su_id, {})

            headers = request.httprequest.headers

            call_id = kwargs.get('call_id', '') or headers.get('X-Call-Id', '')
            user_id = kwargs.get('user_id', '') or headers.get('X-User-Id', '')
            company_id = kwargs.get('company_id', '') or headers.get('X-Company-Id', '')
            orig_name = headers.get('X-Filename', '')

            # 1. Resolve Staff User & Company
            user = False
            if user_id:
                try:
                    target_u = env["res.users"].browse(int(user_id))
                    if target_u.exists() and target_u.login != "public":
                        user = target_u
                except Exception:
                    pass

            if not user:
                user = env["res.users"].search([("share", "=", False), ("login", "!=", "admin")], limit=1)

            company = False
            if company_id:
                try:
                    c = env["res.company"].browse(int(company_id))
                    if c.exists():
                        company = c
                except Exception:
                    pass
            if not company:
                company = user.company_id if user else env.company

            def slugify(text):
                cleaned = re.sub(r'[^a-zA-Z0-9_-]', '_', str(text or 'Unknown')).strip('_')
                return cleaned or 'General'

            comp_slug = slugify(company.name)
            user_slug = slugify(user.name or user.login)

            # 2. Extract clean 10-digit phone
            if not call_id or call_id == 'Unknown':
                # Try finding in filename if X-Call-Id wasn't passed
                m = re.search(r'(\d{10,12})', orig_name or '')
                if m:
                    call_id = m.group(1)

            digits = re.sub(r'\D', '', str(call_id or ''))
            phone_10 = digits[-10:] if len(digits) >= 10 else (digits or 'Unknown')

            # 3. Create nested folder structure with safe fallback:
            save_base_dir = '/opt/odoo19/custom_addons/diyacrm/static/recordings/'
            try:
                os.makedirs(save_base_dir, exist_ok=True)
            except Exception:
                save_base_dir = '/tmp/recordings/'
                os.makedirs(save_base_dir, exist_ok=True)

            target_dir = os.path.join(save_base_dir, comp_slug, user_slug, phone_10)
            os.makedirs(target_dir, exist_ok=True)

            file_obj = request.httprequest.files.get('file')
            if file_obj:
                raw_filename = getattr(file_obj, 'filename', '') or orig_name or 'recording.aac'
                ext = os.path.splitext(raw_filename)[1].lower()
                if ext not in ['.aac', '.m4a', '.mp3', '.amr', '.wav', '.ogg', '.opus', '.3gp']:
                    ext = '.aac'
                clean_orig = re.sub(r'[^a-zA-Z0-9_.-]', '_', raw_filename)
                filename = clean_orig if clean_orig.endswith(ext) else f"{clean_orig}{ext}"
                filepath = os.path.join(target_dir, filename)
                file_obj.save(filepath)
            else:
                raw_data = request.httprequest.get_data() or request.httprequest.data
                if not raw_data:
                    return request.make_response(
                        json.dumps({"status": "error", "message": "Missing file data"}),
                        headers=[('Content-Type', 'application/json')])
                raw_filename = orig_name or 'recording.aac'
                ext = os.path.splitext(raw_filename)[1].lower()
                if ext not in ['.aac', '.m4a', '.mp3', '.amr', '.wav', '.ogg', '.opus', '.3gp']:
                    ext = '.aac'
                clean_orig = re.sub(r'[^a-zA-Z0-9_.-]', '_', raw_filename)
                filename = clean_orig if clean_orig.endswith(ext) else f"{clean_orig}{ext}"
                filepath = os.path.join(target_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(raw_data)
                    f.write(raw_data)

            # Ensure proper read permissions for web streaming
            try:
                os.chmod(filepath, 0o664)
            except Exception:
                pass

            relative_path = f"{comp_slug}/{user_slug}/{phone_10}/{filename}"
            url = f"https://crm.sigprop.in/recordings/{relative_path}"

            # 4. Auto-attach to CRM Lead Chatter
            lead_id = False
            lead_name = False
            if phone_10 and phone_10 != 'Unknown':
                lead = env["crm.lead"].find_lead_by_phone(phone_10, company_id=company.id, active_test=False)
                if not lead:
                    lead = env["crm.lead"].find_lead_by_phone(phone_10, company_id=None, active_test=False)
                if not lead:
                    Lead = env["crm.lead"].with_context(active_test=False)
                    domain = [
                        "|",
                        ("phone", "ilike", phone_10),
                        ("name", "ilike", phone_10)
                    ]
                    matching_leads = Lead.search([("company_id", "=", company.id)] + domain, order="write_date desc", limit=1)
                    if not matching_leads:
                        matching_leads = Lead.search(domain, order="write_date desc", limit=1)
                    if matching_leads:
                        lead = matching_leads[0]

                if lead:
                    lead_id = lead.id
                    lead_name = lead.name
                    # Check if audio already embedded for this file to prevent duplicate posts
                    player_url = f"https://crm.sigprop.in/play_recording?file={relative_path}"
                    raw_bytes = None
                    try:
                        with open(filepath, 'rb') as af:
                            raw_bytes = af.read()
                    except Exception as _fe:
                        _logger.warning("Could not read file for attachment: %s", str(_fe))

                    btn_html = f'''
                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #cbd5e1;">
                            <div style="margin-top: 4px;">
                                <a href="{player_url}" target="_blank" style="display: inline-block; padding: 7px 16px; background-color: #2563eb; color: #ffffff !important; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #1d4ed8; margin-right: 8px;">
                                    <span style="color: #ffffff !important; font-weight: bold;">▶️ Play Recording</span>
                                </a>
                                <a href="{url}" download="{filename}" style="display: inline-block; padding: 7px 12px; background-color: #ffffff; color: #334155 !important; border: 1px solid #cbd5e1; border-radius: 6px; text-decoration: none; font-size: 11.5px; font-weight: bold;">
                                    <span style="color: #334155 !important; font-weight: bold;">⬇️ Download ({ext.replace('.', '').upper()})</span>
                                </a>
                            </div>
                        </div>
                    '''

                    # Check if there is an existing Dialer Call Log message for this lead
                    recent_dialer_msg = env['mail.message'].search([
                        ('res_id', '=', lead.id),
                        ('model', '=', 'crm.lead'),
                        ('body', 'ilike', 'Auto-Synced via Diya CRM Dialer'),
                    ], order='id desc', limit=1)

                    if recent_dialer_msg and 'Play Recording' not in str(recent_dialer_msg.body):
                        # Merge recording directly into the Call Log card!
                        new_b = str(recent_dialer_msg.body).replace('Auto-Synced via Diya CRM Dialer', btn_html + 'Auto-Synced via Diya CRM Dialer')
                        recent_dialer_msg.write({'body': Markup(new_b)})
                    else:
                        existing_msg = env['mail.message'].search([
                            ('res_id', '=', lead.id),
                            ('model', '=', 'crm.lead'),
                            '|',
                            ('body', 'ilike', relative_path),
                            ('body', 'ilike', filename)
                        ], limit=1)

                        if not existing_msg:
                            chatter_audio = Markup(f'''
                                <div style="padding: 12px 16px; border-left: 4px solid #2563eb; background-color: #f8fafc; border-radius: 8px; margin: 6px 0; border: 1px solid #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                                    <div style="margin-bottom: 6px;">
                                        <span style="font-weight: bold; color: #1e40af; font-size: 13.5px;">
                                            🔊 Call Recording Auto-Attached
                                        </span>
                                        <span style="font-weight: bold; color: #1e40af; background-color: #dbeafe; padding: 2px 10px; border-radius: 12px; font-size: 11px; margin-left: 8px;">
                                            {company.name}
                                        </span>
                                    </div>
                                    <div style="font-size: 12px; color: #475569; margin-bottom: 8px;">
                                        <b>Staff:</b> {user.name} &nbsp;|&nbsp; <b>Client:</b> <span style="color: #1e293b; font-weight: bold;">{phone_10}</span>
                                    </div>
                                    <div style="margin-bottom: 8px;">
                                        <a href="{player_url}" target="_blank" style="display: inline-block; padding: 7px 16px; background-color: #2563eb; color: #ffffff !important; border-radius: 6px; text-decoration: none; font-size: 12.5px; font-weight: bold; border: 1px solid #1d4ed8; margin-right: 8px;">
                                            <span style="color: #ffffff !important; font-weight: bold;">▶️ Play Recording</span>
                                        </a>
                                        <a href="{url}" download="{filename}" style="display: inline-block; padding: 7px 12px; background-color: #ffffff; color: #334155 !important; border: 1px solid #cbd5e1; border-radius: 6px; text-decoration: none; font-size: 11.5px; font-weight: bold;">
                                            <span style="color: #334155 !important; font-weight: bold;">⬇️ Download ({ext.replace('.', '').upper()})</span>
                                        </a>
                                    </div>
                                    <div style="font-size: 11px; color: #94a3b8;">
                                        Auto-Synced via DiyaSync &bull; File: {filename}
                                    </div>
                                </div>
                            ''')

                            post_kwargs = {
                                "body": chatter_audio,
                                "message_type": "comment",
                                "subtype_xmlid": "mail.mt_note",
                                "author_id": user.partner_id.id if user else False,
                            }
                            lead.message_post(**post_kwargs)

            import json
            return request.make_response(
                json.dumps({
                    "status": "success",
                    "url": url,
                    "company": company.name,
                    "user": user.name,
                    "lead_id": lead_id,
                    "lead_name": lead_name,
                    "folder": f"{comp_slug}/{user_slug}/{phone_10}"
                }, separators=(',', ':')),
                headers=[('Content-Type', 'application/json')])
        except Exception as e:
            _logger.exception("Upload recording error: %s", str(e))
            import json
            return request.make_response(
                json.dumps({"status": "error", "message": str(e)}, separators=(',', ':')),
                headers=[('Content-Type', 'application/json')])

    @http.route('/play_recording', type='http', auth='public', methods=['GET'])
    def play_recording_page(self, file=None, **kwargs):
        if not file:
            return request.not_found("Missing recording file parameter.")
        clean_file = file.replace('\\', '/').strip('/')
        if '..' in clean_file or clean_file.startswith('/'):
            return request.not_found("Invalid path.")

        file_path = os.path.join('/opt/odoo19/custom_addons/diyacrm/static/recordings/', clean_file)
        if not os.path.exists(file_path):
            return request.not_found("Recording file not found on server.")

        stream_url = f"/recordings/{clean_file}"
        download_url = f"/recordings/{clean_file}"
        parts = clean_file.split('/')
        company_name = parts[0].replace('_', ' ') if len(parts) > 0 else 'CRM'
        staff_name = parts[1].replace('_', ' ') if len(parts) > 1 else 'Staff'
        client_phone = parts[2] if len(parts) > 2 else 'Client'
        filename = parts[-1] if len(parts) > 0 else 'recording'
        filesize_kb = round(os.path.getsize(file_path) / 1024, 1)

        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.m4a', '.mp4']:
            primary_type = 'audio/mp4'
        elif ext == '.mp3':
            primary_type = 'audio/mpeg'
        elif ext == '.aac':
            primary_type = 'audio/aac'
        elif ext in ['.ogg', '.oga']:
            primary_type = 'audio/ogg'
        elif ext == '.wav':
            primary_type = 'audio/wav'
        elif ext == '.amr':
            primary_type = 'audio/amr'
        else:
            primary_type = 'audio/mp4'

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Call Recording - {client_phone} | Diya CRM</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: #f8fafc;
        }}
        .player-card {{
            background: rgba(30, 41, 59, 0.85);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 32px 28px;
            width: 100%;
            max-width: 480px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            text-align: center;
        }}
        .pulse-icon {{
            width: 72px;
            height: 72px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, #2563eb, #3b82f6);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            box-shadow: 0 0 24px rgba(37, 99, 235, 0.4);
            animation: pulse 2s infinite ease-in-out;
        }}
        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.05); }}
        }}
        .title {{
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 6px;
            color: #ffffff;
        }}
        .client-badge {{
            display: inline-block;
            background: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 20px;
            letter-spacing: 0.5px;
        }}
        .meta-grid {{
            background: rgba(15, 23, 42, 0.6);
            border-radius: 12px;
            padding: 14px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            text-align: left;
            font-size: 12px;
            margin-bottom: 24px;
        }}
        .meta-item b {{
            display: block;
            color: #94a3b8;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 2px;
        }}
        .meta-item span {{
            color: #e2e8f0;
            font-weight: 600;
        }}
        audio {{
            width: 100%;
            height: 48px;
            border-radius: 8px;
            outline: none;
            margin-bottom: 16px;
        }}
        .notice-box {{
            display: none;
            margin-bottom: 18px;
            padding: 10px 14px;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            font-size: 12px;
            color: #fca5a5;
            text-align: left;
            line-height: 1.4;
        }}
        .speed-control {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            margin-bottom: 22px;
        }}
        .speed-label {{
            font-size: 12px;
            color: #94a3b8;
            font-weight: 600;
            margin-right: 4px;
        }}
        .speed-btn {{
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: #cbd5e1;
            padding: 5px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .speed-btn.active {{
            background: #2563eb;
            color: #ffffff;
            border-color: #2563eb;
            box-shadow: 0 0 10px rgba(37, 99, 235, 0.5);
        }}
        .btn-group {{
            display: flex;
            gap: 12px;
            justify-content: center;
        }}
        .btn {{
            flex: 1;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 20px;
            border-radius: 10px;
            text-decoration: none;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        .btn-download {{
            background: #2563eb;
            color: #ffffff;
        }}
        .btn-download:hover {{
            background: #1d4ed8;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }}
        .btn-back {{
            background: rgba(255, 255, 255, 0.1);
            color: #cbd5e1;
        }}
        .btn-back:hover {{
            background: rgba(255, 255, 255, 0.15);
            color: #ffffff;
        }}
        .file-note {{
            font-size: 11px;
            color: #64748b;
            margin-top: 18px;
            word-break: break-all;
        }}
    </style>
</head>
<body>
    <div class="player-card">
        <div class="pulse-icon">🎙️</div>
        <h1 class="title">Call Recording</h1>
        <div class="client-badge">📞 {client_phone}</div>

        <div class="meta-grid">
            <div class="meta-item">
                <b>Staff</b>
                <span>{staff_name}</span>
            </div>
            <div class="meta-item">
                <b>Company</b>
                <span>{company_name}</span>
            </div>
            <div class="meta-item">
                <b>File Size</b>
                <span>{filesize_kb} KB</span>
            </div>
            <div class="meta-item">
                <b>Status</b>
                <span style="color: #22c55e;">Synced & Ready</span>
            </div>
        </div>

        <audio id="audioPlayer" controls autoplay preload="auto">
            <source src="{stream_url}" type="{primary_type}">
            <source src="{stream_url}">
            Your browser does not support audio playback.
        </audio>

        <div id="noticeBox" class="notice-box">
            ⚠️ <b>Playback issue detected:</b> Yeh audio format browser me direct play nahi ho raha hai (codec / incomplete stream). Kripya niche <b>Download Audio</b> button daba kar phone ya VLC me open karein.
        </div>

        <div class="speed-control">
            <span class="speed-label">Speed:</span>
            <button class="speed-btn active" onclick="setSpeed(1.0, this)">1.0x</button>
            <button class="speed-btn" onclick="setSpeed(1.25, this)">1.25x</button>
            <button class="speed-btn" onclick="setSpeed(1.5, this)">1.5x</button>
            <button class="speed-btn" onclick="setSpeed(2.0, this)">2.0x</button>
        </div>

        <div class="btn-group">
            <a href="{download_url}" download="{filename}" class="btn btn-download">
                ⬇️ Download Audio
            </a>
            <button onclick="window.close()" class="btn btn-back">
                ✕ Close
            </button>
        </div>

        <div class="file-note">
            File: {filename}
        </div>
    </div>

    <script>
        const audio = document.getElementById('audioPlayer');
        const notice = document.getElementById('noticeBox');
        if (audio) {{
            audio.addEventListener('error', function(e) {{
                console.warn('Audio playback error encountered:', e);
                if (notice) notice.style.display = 'block';
            }});
        }}
        function setSpeed(rate, btn) {{
            if (audio) audio.playbackRate = rate;
            document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        }}
    </script>
</body>
</html>
"""
        return Response(html_content, headers=[("Content-Type", "text/html; charset=utf-8")])

    @http.route('/recordings/<path:filename>', type='http', auth='public', methods=['GET'])
    def stream_recording(self, filename):
        file_path = os.path.join('/opt/odoo19/custom_addons/diyacrm/static/recordings/', filename)
        if not os.path.exists(file_path):
            return request.not_found("Recording not found.")

        ext = os.path.splitext(filename)[1].lower()
        mime_map = {
            '.aac': 'audio/aac',
            '.m4a': 'audio/mp4',
            '.mp4': 'audio/mp4',
            '.mp3': 'audio/mpeg',
            '.amr': 'audio/amr',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
        }
        content_type = mime_map.get(ext, 'audio/mp4')
        file_size = os.path.getsize(file_path)

        range_header = request.httprequest.headers.get('Range', None)
        if range_header and range_header.startswith('bytes='):
            try:
                ranges = range_header.replace('bytes=', '').strip().split('-')
                start = int(ranges[0]) if ranges[0] else 0
                end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1
                if start >= file_size or end >= file_size or start > end:
                    return Response(status=416, headers={"Content-Range": f"bytes */{file_size}"})

                length = end - start + 1
                with open(file_path, "rb") as f:
                    f.seek(start)
                    data = f.read(length)

                return Response(
                    data,
                    status=206,
                    headers=[
                        ("Content-Type", content_type),
                        ("Content-Range", f"bytes {start}-{end}/{file_size}"),
                        ("Content-Length", str(length)),
                        ("Content-Disposition", f"inline; filename={os.path.basename(filename)}"),
                        ("Accept-Ranges", "bytes")
                    ]
                )
            except Exception:
                pass

        with open(file_path, "rb") as f:
            data = f.read()

        return Response(
            data,
            status=200,
            headers=[
                ("Content-Type", content_type),
                ("Content-Length", str(file_size)),
                ("Content-Disposition", f"inline; filename={os.path.basename(filename)}"),
                ("Accept-Ranges", "bytes")
            ]
        )

    def _find_recording_on_server(self, phone_number, start_time=None):
        import os, re
        base_dir = '/opt/odoo19/custom_addons/diyacrm/static/recordings/'
        if not os.path.exists(base_dir):
            return None
        clean_phone = re.sub(r'\D', '', str(phone_number or ''))
        if len(clean_phone) > 10:
            clean_phone = clean_phone[-10:]
        if not clean_phone:
            return None

        audio_exts = ('.aac', '.m4a', '.mp3', '.amr', '.wav', '.ogg')
        matches = []
        try:
            for root, dirs, files in os.walk(base_dir):
                for f in files:
                    if f.lower().endswith(audio_exts):
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, base_dir).replace('\\', '/')
                        if clean_phone in rel_path:
                            mtime = os.path.getmtime(full_path)
                            matches.append((rel_path, mtime))
            if matches:
                matches.sort(key=lambda x: x[1], reverse=True)
                return 'https://crm.sigprop.in/recordings/' + matches[0][0]
        except Exception as e:
            _logger.warning("Error searching server recording: %s", str(e))
        return None

    @http.route('/api/call_tracker/sync_server_recordings', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def sync_server_recordings(self, **kwargs):
        import os, re
        base_dir = '/opt/odoo19/custom_addons/diyacrm/static/recordings/'
        if not os.path.exists(base_dir):
            return {"status": "no_dir"}
        env = request.env(user=SUPERUSER_ID, su=True)
        messages = env['mail.message'].search([
            ('model', '=', 'crm.lead'),
            ('body', 'ilike', 'Auto-Synced via Diya CRM Dialer')
        ], order='id desc', limit=50)

        audio_exts = ('.aac', '.m4a', '.mp3', '.amr', '.wav', '.ogg')
        all_recordings = []
        for root, dirs, files in os.walk(base_dir):
            for f in files:
                if f.lower().endswith(audio_exts):
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, base_dir).replace('\\', '/')
                    all_recordings.append((rel_p, os.path.getmtime(full_p)))
        all_recordings.sort(key=lambda x: x[1], reverse=True)

        linked_count = 0
        for msg in messages:
            if 'Play Recording' in (msg.body or ''):
                continue
            lead = env['crm.lead'].browse(msg.res_id)
            phone = lead.phone or lead.mobile or ''
            clean_phone = re.sub(r'\D', '', str(phone))
            if len(clean_phone) > 10:
                clean_phone = clean_phone[-10:]
            if not clean_phone:
                continue

            for rel_p, mtime in all_recordings:
                if clean_phone in rel_p:
                    player_url = f"https://crm.sigprop.in/play_recording?file={rel_p}"
                    rec_url = 'https://crm.sigprop.in/recordings/' + rel_p
                    player = f'''
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #cbd5e1;">
                        <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                            <a href="{player_url}" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; padding: 7px 16px; background: #2563eb; color: #ffffff !important; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 700; box-shadow: 0 2px 4px rgba(37,99,235,0.25);">
                                ▶️ Play Recording
                            </a>
                            <a href="{rec_url}" download style="display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; background: #ffffff; color: #334155 !important; border: 1px solid #cbd5e1; border-radius: 6px; text-decoration: none; font-size: 11.5px; font-weight: 600;">
                                ⬇️ Download
                            </a>
                        </div>
                    </div>
                    '''
                    new_b = str(msg.body).replace('Auto-Synced via Diya CRM Dialer', player + 'Auto-Synced via Diya CRM Dialer')
                    msg.write({'body': Markup(new_b)})
                    linked_count += 1
                    break
        return {"status": "success", "linked": linked_count}

    @http.route('/api/call_tracker/update_recording', type='jsonrpc', auth='public',
                methods=['POST'], csrf=False)
    def update_recording(self, call_id=None, recording_url=None, **kwargs):
        import time
        try:
            if not call_id or not recording_url:
                return {"status": "error", "message": "Missing params"}
            env = request.env(user=SUPERUSER_ID, su=True)
            target_msg = False
            for _ in range(4):
                target_msg = env['mail.message'].search([
                    ('model', '=', 'crm.lead'),
                    ('body', 'ilike', 'Auto-Synced via Diya CRM Dialer')
                ], order='id desc', limit=1)
                if target_msg:
                    break
                time.sleep(1.0)
            if target_msg:
                rel_p = recording_url.replace("https://crm.sigprop.in/recordings/", "")
                player_url = f"https://crm.sigprop.in/play_recording?file={rel_p}"
                audio_html = f'''
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #cbd5e1;">
                        <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                            <a href="{player_url}" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; padding: 7px 16px; background: #2563eb; color: #ffffff !important; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 700; box-shadow: 0 2px 4px rgba(37,99,235,0.25);">
                                ▶️ Play Recording
                            </a>
                            <a href="{recording_url}" download style="display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; background: #ffffff; color: #334155 !important; border: 1px solid #cbd5e1; border-radius: 6px; text-decoration: none; font-size: 11.5px; font-weight: 600;">
                                ⬇️ Download
                            </a>
                        </div>
                    </div>
                '''
                if 'Auto-Synced via Diya CRM Dialer' in str(target_msg.body) and 'Play Recording' not in str(target_msg.body):
                    new_b = str(target_msg.body).replace('Auto-Synced via Diya CRM Dialer', audio_html + 'Auto-Synced via Diya CRM Dialer')
                    target_msg.write({'body': Markup(new_b)})
                return {"status": "success", "message": "Recording audio added to chatter"}
            return {"status": "not_found"}
        except Exception as e:
            _logger.exception("Update recording error: %s", str(e))
            return {"status": "error", "message": str(e)}

    @http.route('/api/call_tracker/upgrade_past_recordings', type='http', auth='public', methods=['GET'])
    def upgrade_past_recordings(self, **kwargs):
        env = request.env(user=SUPERUSER_ID, su=True)
        messages = env['mail.message'].search([
            ('model', '=', 'crm.lead'),
            ('body', 'ilike', 'DiyaSync')
        ], order='id desc', limit=100)

        updated_count = 0
        deleted_count = 0
        base_dir = '/opt/odoo19/custom_addons/diyacrm/static/recordings/'

        recordings = []
        if os.path.exists(base_dir):
            for root, dirs, files in os.walk(base_dir):
                for f in files:
                    if f.lower().endswith(('.aac', '.m4a', '.mp3', '.amr', '.wav', '.ogg')):
                        fp = os.path.join(root, f)
                        rel_p = os.path.relpath(fp, base_dir).replace('\\', '/')
                        recordings.append((rel_p, f, os.path.getmtime(fp)))
        recordings.sort(key=lambda x: x[2], reverse=True)

        # Delete existing audio attachments so the big square card in chatter disappears!
        audio_attachments = env['ir.attachment'].search([
            ('res_model', 'in', ['crm.lead', 'mail.message']),
            '|', '|', '|',
            ('name', 'ilike', '.aac'),
            ('name', 'ilike', '.m4a'),
            ('name', 'ilike', '.mp3'),
            ('name', 'ilike', '.amr')
        ])
        att_deleted = len(audio_attachments)
        if audio_attachments:
            try:
                audio_attachments.unlink()
            except Exception:
                pass

        seen_lead_time = set()
        for msg in messages:
            lead = env['crm.lead'].browse(msg.res_id)
            if not lead.exists():
                continue

            phone = re.sub(r'\D', '', str(lead.phone or lead.mobile or ''))
            if len(phone) > 10:
                phone = phone[-10:]

            # Deduplicate messages for same lead created around the same time
            time_key = (msg.res_id, msg.date.strftime('%Y-%m-%d %H') if msg.date else '')
            if time_key in seen_lead_time:
                try:
                    msg.unlink()
                    deleted_count += 1
                except Exception:
                    pass
                continue
            seen_lead_time.add(time_key)

            match_rel = None
            match_fname = None
            for rel_p, fname, mtime in recordings:
                if phone and phone in rel_p:
                    match_rel = rel_p
                    match_fname = fname
                    break

            if match_rel:
                player_url = f"https://crm.sigprop.in/play_recording?file={match_rel}"
                dl_url = f"https://crm.sigprop.in/recordings/{match_rel}"
                comp_name = lead.company_id.name or "The 1st Residency"
                staff_name = msg.author_id.name or "Shivam"
                ext = os.path.splitext(match_fname)[1].lower().replace('.', '').upper()

                btn_html = f'''
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #cbd5e1;">
                        <div style="margin-top: 4px;">
                            <a href="{player_url}" target="_blank" style="display: inline-block; padding: 7px 16px; background-color: #2563eb; color: #ffffff !important; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #1d4ed8; margin-right: 8px;">
                                <span style="color: #ffffff !important; font-weight: bold;">▶️ Play Recording</span>
                            </a>
                            <a href="{dl_url}" download="{match_fname}" style="display: inline-block; padding: 7px 12px; background-color: #ffffff; color: #334155 !important; border: 1px solid #cbd5e1; border-radius: 6px; text-decoration: none; font-size: 11.5px; font-weight: bold;">
                                <span style="color: #334155 !important; font-weight: bold;">⬇️ Download ({ext})</span>
                            </a>
                        </div>
                    </div>
                '''

                # Check if this lead has a Dialer Call Log message
                recent_dialer = env['mail.message'].search([
                    ('res_id', '=', lead.id),
                    ('model', '=', 'crm.lead'),
                    ('body', 'ilike', 'Auto-Synced via Diya CRM Dialer')
                ], order='id desc', limit=1)

                if recent_dialer and 'Play Recording' not in str(recent_dialer.body):
                    new_b = str(recent_dialer.body).replace('Auto-Synced via Diya CRM Dialer', btn_html + 'Auto-Synced via Diya CRM Dialer')
                    recent_dialer.write({'body': Markup(new_b)})
                    # Now that it's merged into the call log, delete the separate DiyaSync card
                    try:
                        msg.unlink()
                        deleted_count += 1
                    except Exception:
                        pass
                    updated_count += 1
                else:
                    clean_card = Markup(f'''
                        <div style="padding: 12px 16px; border-left: 4px solid #2563eb; background-color: #f8fafc; border-radius: 8px; margin: 6px 0; border: 1px solid #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                            <div style="margin-bottom: 6px;">
                                <span style="font-weight: bold; color: #1e40af; font-size: 13.5px;">
                                    🔊 Call Recording Auto-Attached
                                </span>
                                <span style="font-weight: bold; color: #1e40af; background-color: #dbeafe; padding: 2px 10px; border-radius: 12px; font-size: 11px; margin-left: 8px;">
                                    {comp_name}
                                </span>
                            </div>
                            <div style="font-size: 12px; color: #475569; margin-bottom: 8px;">
                                <b>Staff:</b> {staff_name} &nbsp;|&nbsp; <b>Client:</b> <span style="color: #1e293b; font-weight: bold;">{phone}</span>
                            </div>
                            <div style="margin-bottom: 8px;">
                                <a href="{player_url}" target="_blank" style="display: inline-block; padding: 7px 16px; background-color: #2563eb; color: #ffffff !important; border-radius: 6px; text-decoration: none; font-size: 12.5px; font-weight: bold; border: 1px solid #1d4ed8; margin-right: 8px;">
                                    <span style="color: #ffffff !important; font-weight: bold;">▶️ Play Recording</span>
                                </a>
                                <a href="{dl_url}" download="{match_fname}" style="display: inline-block; padding: 7px 12px; background-color: #ffffff; color: #334155 !important; border: 1px solid #cbd5e1; border-radius: 6px; text-decoration: none; font-size: 11.5px; font-weight: bold;">
                                    <span style="color: #334155 !important; font-weight: bold;">⬇️ Download ({ext})</span>
                                </a>
                            </div>
                            <div style="font-size: 11px; color: #94a3b8;">
                                Auto-Synced via DiyaSync &bull; File: {match_fname}
                            </div>
                        </div>
                    ''')
                    msg.write({'body': clean_card})
                    updated_count += 1

        return Response(
            f"Successfully updated {updated_count} messages with Play button and cleaned {deleted_count} duplicate messages!",
            content_type="text/plain"
        )


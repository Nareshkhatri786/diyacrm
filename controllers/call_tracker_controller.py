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

            target_company_id = int(company_id) if company_id else (user.company_id.id if user else env.company.id)
            if user and user.company_id.id != target_company_id:
                target_company_id = user.company_id.id

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

            # First try matching in user's company
            matching_leads = Lead.search([("company_id", "=", target_company_id)] + domain, order="write_date desc")
            if not matching_leads:
                # If not found in primary company, search globally across all companies
                matching_leads = Lead.search(domain, order="write_date desc")

            # Prioritize real named leads over previously auto-generated 'Call:' leads
            real_leads = matching_leads.filtered(lambda l: not (l.name.startswith("Call:") or l.name.startswith("+91")))
            lead = real_leads[0] if real_leads else (matching_leads[0] if matching_leads else False)

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
                if "lead_temperature" in env["crm.lead"]._fields:
                    update_vals["lead_temperature"] = "hot"
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
            if recording_url:
                audio_player_html = f'''
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #cbd5e1;">
                        <span style="font-size: 12px; font-weight: 700; color: #334155;">🔊 Call Recording:</span>
                        <div style="margin-top: 4px;">
                            <audio controls style="width: 100%; height: 32px; outline: none;" preload="metadata">
                                <source src="{recording_url}" type="audio/aac">
                                <source src="{recording_url}" type="audio/mp4">
                                <source src="{recording_url}" type="audio/mpeg">
                                <source src="{recording_url}" type="audio/amr">
                                Your browser does not support the audio element.
                            </audio>
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


    @http.route('/api/call_tracker/upload_recording', type='http', auth='none',
                methods=['POST'], csrf=False)
    def upload_recording(self, **kwargs):
        import os, time
        try:
            call_id = kwargs.get('call_id', '')
            file_obj = request.httprequest.files.get('file')
            if not file_obj or not call_id:
                return request.make_response(
                    '{"status":"error","message":"Missing file or call_id"}',
                    headers=[('Content-Type', 'application/json')])

            save_dir = '/opt/odoo19/custom_addons/diyacrm/static/recordings/'
            os.makedirs(save_dir, exist_ok=True)
            orig_name = getattr(file_obj, 'filename', '') or ''
            ext = os.path.splitext(orig_name)[1].lower()
            if ext not in ['.aac', '.m4a', '.mp3', '.amr', '.wav', '.ogg']:
                ext = '.aac' if 'aac' in orig_name.lower() else ('.m4a' if 'm4a' in orig_name.lower() else ('.mp3' if 'mp3' in orig_name.lower() else '.amr'))
            filename = 'call_{}_{}{}'.format(
                call_id.replace('/', '_'), int(time.time()), ext)
            filepath = os.path.join(save_dir, filename)
            file_obj.save(filepath)
            url = 'https://crm.sigprop.in/recordings/' + filename
            import json
            return request.make_response(
                json.dumps({"status": "success", "url": url}, separators=(',', ':')),
                headers=[('Content-Type', 'application/json')])
        except Exception as e:
            _logger.exception("Upload recording error: %s", str(e))
            import json
            return request.make_response(
                json.dumps({"status": "error", "message": str(e)}, separators=(',', ':')),
                headers=[('Content-Type', 'application/json')])

    @http.route('/recordings/<string:filename>', type='http', auth='public', methods=['GET'])
    def stream_recording(self, filename):
        file_path = os.path.join('/opt/odoo19/custom_addons/diyacrm/static/recordings/', filename)
        if not os.path.exists(file_path):
            return request.not_found("Recording not found.")
        with open(file_path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(filename)[1].lower()
        mime_map = {
            '.aac': 'audio/aac',
            '.m4a': 'audio/mp4',
            '.mp3': 'audio/mpeg',
            '.amr': 'audio/amr',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
        }
        content_type = mime_map.get(ext, 'audio/aac')
        return request.make_response(data, headers=[
            ("Content-Type", content_type),
            ("Content-Disposition", f"inline; filename={filename}"),
            ("Accept-Ranges", "bytes")
        ])

    @http.route('/api/call_tracker/update_recording', type='json', auth='public',
                methods=['POST'], csrf=False)
    def update_recording(self, call_id=None, recording_url=None, **kwargs):
        import time
        try:
            if not call_id or not recording_url:
                return {"status": "error", "message": "Missing params"}
            env = request.env(user=SUPERUSER_ID, su=True)
            # Search latest call log message on lead (retry up to 4 times to ensure sync_call completed)
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
                audio_html = f'''
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #cbd5e1;">
                        <span style="font-size: 12px; font-weight: 700; color: #334155;">🔊 Call Recording:</span>
                        <div style="margin-top: 4px;">
                            <audio controls style="width: 100%; height: 32px; outline: none;" preload="metadata">
                                <source src="{recording_url}" type="audio/aac">
                                <source src="{recording_url}" type="audio/mp4">
                                <source src="{recording_url}" type="audio/mpeg">
                                <source src="{recording_url}" type="audio/amr">
                                Your browser does not support the audio element.
                            </audio>
                        </div>
                    </div>
                '''
                if 'Auto-Synced via Diya CRM Dialer' in target_msg.body and 'Call Recording:' not in target_msg.body:
                    target_msg.body = Markup(target_msg.body.replace('Auto-Synced via Diya CRM Dialer', audio_html + 'Auto-Synced via Diya CRM Dialer'))
                return {"status": "success", "message": "Recording audio added to chatter"}
            return {"status": "not_found"}
        except Exception as e:
            _logger.exception("Update recording error: %s", str(e))
            return {"status": "error", "message": str(e)}

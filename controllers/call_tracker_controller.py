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


    @http.route('/api/call_tracker/upload_recording', type='http', auth='none',
                methods=['POST'], csrf=False)
    def upload_recording(self, **kwargs):
        import os, time, re
        try:
            env = request.env(user=SUPERUSER_ID, su=True)
            headers = request.httprequest.headers

            call_id = kwargs.get('call_id', '') or headers.get('X-Call-Id', '')
            user_id = kwargs.get('user_id', '') or headers.get('X-User-Id', '')
            company_id = kwargs.get('company_id', '') or headers.get('X-Company-Id', '')

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
            digits = re.sub(r'\D', '', str(call_id or ''))
            phone_10 = digits[-10:] if len(digits) >= 10 else (digits or 'Unknown')

            # 3. Create nested folder structure:
            # /opt/odoo19/custom_addons/diyacrm/static/recordings/[Company]/[User]/[Phone]/
            save_base_dir = '/opt/odoo19/custom_addons/diyacrm/static/recordings/'
            target_dir = os.path.join(save_base_dir, comp_slug, user_slug, phone_10)
            os.makedirs(target_dir, exist_ok=True)

            file_obj = request.httprequest.files.get('file')
            if file_obj:
                orig_name = getattr(file_obj, 'filename', '') or ''
                ext = os.path.splitext(orig_name)[1].lower()
                if ext not in ['.aac', '.m4a', '.mp3', '.amr', '.wav', '.ogg']:
                    ext = '.aac' if 'aac' in orig_name.lower() else ('.m4a' if 'm4a' in orig_name.lower() else ('.mp3' if 'mp3' in orig_name.lower() else '.amr'))
                clean_orig = re.sub(r'[^a-zA-Z0-9_.-]', '_', orig_name) if orig_name else f"rec_{int(time.time())}{ext}"
                filename = clean_orig if clean_orig.endswith(ext) else f"{clean_orig}{ext}"
                filepath = os.path.join(target_dir, filename)
                file_obj.save(filepath)
            else:
                raw_data = request.httprequest.data
                if not raw_data or not call_id:
                    return request.make_response(
                        '{"status":"error","message":"Missing file or call_id"}',
                        headers=[('Content-Type', 'application/json')])
                orig_name = headers.get('X-Filename', '') or 'recording.aac'
                ext = os.path.splitext(orig_name)[1].lower()
                if ext not in ['.aac', '.m4a', '.mp3', '.amr', '.wav', '.ogg']:
                    ext = '.aac' if 'aac' in orig_name.lower() else ('.m4a' if 'm4a' in orig_name.lower() else ('.mp3' if 'mp3' in orig_name.lower() else '.amr'))
                clean_orig = re.sub(r'[^a-zA-Z0-9_.-]', '_', orig_name) if orig_name else f"rec_{int(time.time())}{ext}"
                filename = clean_orig if clean_orig.endswith(ext) else f"{clean_orig}{ext}"
                filepath = os.path.join(target_dir, filename)
                with open(filepath, 'wb') as f:
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
            margin-bottom: 20px;
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
            <source src="{stream_url}" type="audio/aac">
            <source src="{stream_url}" type="audio/mp4">
            <source src="{stream_url}" type="audio/mpeg">
            <source src="{stream_url}">
            Your browser does not support audio playback.
        </audio>

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

    @http.route('/api/call_tracker/sync_server_recordings', type='json', auth='public', methods=['POST'], csrf=False)
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

    @http.route('/api/call_tracker/update_recording', type='json', auth='public',
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


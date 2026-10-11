# -*- coding: utf-8 -*-
"""
Diya CRM: Script to scan audio recordings on server and sync/link them with CRM Leads.
- Finds all audio files in /opt/odoo19/custom_addons/diyacrm/static/recordings/
- Extracts phone numbers and timestamps
- Matches with existing crm.lead or creates a call log in chatter
- Updates existing chatter call entries with Play & Download buttons if missing
- Safe, non-destructive, can be run multiple times

Usage:
    python3 scripts/sync_server_recordings_to_crm.py
"""
import os
import sys
import re
import datetime
import subprocess

def find_odoo_execution_command():
    service_files = [
        "/etc/systemd/system/odoo19.service",
        "/etc/systemd/system/odoo.service",
        "/lib/systemd/system/odoo19.service",
    ]
    for s_path in service_files:
        if os.path.exists(s_path):
            try:
                with open(s_path, "r") as sf:
                    for line in sf:
                        if line.strip().startswith("ExecStart="):
                            cmd_str = line.strip().split("=", 1)[1].strip()
                            parts = cmd_str.split()
                            if parts:
                                py_bin = parts[0]
                                odoo_bin = parts[1] if len(parts) > 1 and (parts[1].endswith(".py") or "odoo-bin" in parts[1]) else "/opt/odoo19/odoo/odoo-bin"
                                conf = "/etc/odoo19.conf"
                                if "-c" in parts:
                                    c_idx = parts.index("-c")
                                    if c_idx + 1 < len(parts):
                                        conf = parts[c_idx + 1]
                                return py_bin, odoo_bin, conf
            except Exception:
                pass

    candidate_py = [
        "/opt/odoo19/venv/bin/python3",
        "/opt/odoo19-venv/bin/python3",
        "/usr/bin/python3",
    ]
    py_found = next((p for p in candidate_py if os.path.exists(p)), sys.executable)
    odoo_bin_found = "/opt/odoo19/odoo/odoo-bin" if os.path.exists("/opt/odoo19/odoo/odoo-bin") else "/opt/odoo19/odoo-bin"
    return py_found, odoo_bin_found, "/etc/odoo19.conf"

def run():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    addon_dir = os.path.dirname(script_dir)
    recordings_dir = os.path.join(addon_dir, 'static', 'recordings')

    print("=" * 65)
    print(" 🎙️ DIYA CRM: Sync Unsynced Server Recordings with Leads")
    print("=" * 65)
    print(f"• Addon Dir     : {addon_dir}")
    print(f"• Recordings Dir: {recordings_dir}")

    if not os.path.exists(recordings_dir):
        print(f"⚠️ Notice: Recordings directory '{recordings_dir}' does not exist yet. Creating it...")
        os.makedirs(recordings_dir, exist_ok=True)

    py_bin, odoo_bin, conf = find_odoo_execution_command()
    print(f"• Python Binary : {py_bin}")
    print(f"• Odoo Binary   : {odoo_bin}")
    print(f"• Config File   : {conf}")

    # Shell script to execute inside Odoo ORM
    shell_code = r'''
import os
import re
import datetime
from markupsafe import Markup
from odoo import SUPERUSER_ID, fields

base_dir = '/opt/odoo19/custom_addons/diyacrm/static/recordings/'
audio_exts = ('.aac', '.m4a', '.mp3', '.amr', '.wav', '.ogg')

print("\n🔍 Scanning directory:", base_dir)
if not os.path.exists(base_dir):
    print("❌ Directory not found:", base_dir)
else:
    all_files = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith(audio_exts):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, base_dir).replace('\\', '/')
                mtime = os.path.getmtime(full_path)
                all_files.append((f, rel_path, mtime, full_path))

    print(f"📂 Total Audio Recordings Found on Server: {len(all_files)}")

    # 1. Update existing messages in chatter missing the audio player
    updated_existing = 0
    msgs = env['mail.message'].search([
        ('model', '=', 'crm.lead'),
        ('body', 'ilike', 'Auto-Synced via Diya CRM Dialer')
    ], order='id desc')

    for msg in msgs:
        if 'Play Recording' in (msg.body or ''):
            continue
        lead = env['crm.lead'].browse(msg.res_id)
        if not lead.exists():
            continue
        phone = lead.phone or ''
        clean_phone = re.sub(r'\D', '', str(phone))
        if len(clean_phone) > 10:
            clean_phone = clean_phone[-10:]
        if not clean_phone or len(clean_phone) < 10:
            continue

        for fname, rel_p, mtime, full_p in all_files:
            if clean_phone in fname or clean_phone in rel_p:
                player_url = f"https://crm.sigprop.in/play_recording?file={rel_p}"
                rec_url = f"https://crm.sigprop.in/recordings/{rel_p}"
                player = f"""
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #cbd5e1;">
                    <div style="margin-top: 4px;">
                        <a href="{player_url}" target="_blank" style="display: inline-block; padding: 7px 16px; background-color: #2563eb; color: #ffffff !important; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #1d4ed8; margin-right: 8px;">
                            <span style="color: #ffffff !important; font-weight: bold;">▶️ Play Recording</span>
                        </a>
                        <a href="{rec_url}" download style="display: inline-block; padding: 7px 12px; background-color: #ffffff; color: #334155 !important; border: 1px solid #cbd5e1; border-radius: 6px; text-decoration: none; font-size: 11.5px; font-weight: bold;">
                            <span style="color: #334155 !important; font-weight: bold;">⬇️ Download</span>
                        </a>
                    </div>
                </div>
                """
                new_b = str(msg.body).replace('Auto-Synced via Diya CRM Dialer', player + 'Auto-Synced via Diya CRM Dialer')
                msg.write({'body': Markup(new_b)})
                updated_existing += 1
                break

    print(f"✅ Updated {updated_existing} existing chatter call messages with Play/Download buttons.")

    # 2. For audio files not yet in chatter, attach to matching lead
    newly_synced = 0
    default_company = env['res.company'].search([], limit=1)
    admin_user = env['res.users'].search([('share', '=', False), ('active', '=', True)], limit=1)

    for fname, rel_p, mtime, full_p in all_files:
        # Extract 10-digit phone from filename
        nums = re.findall(r'\d{10}', fname)
        phone_10 = nums[0] if nums else None
        if not phone_10:
            # Try 11 or 12 digit (with 0 or 91)
            long_nums = re.findall(r'\d{11,12}', fname)
            if long_nums:
                digits = long_nums[0]
                phone_10 = digits[-10:]

        if not phone_10:
            continue

        # Check if already in chatter for this specific recording file
        existing_msg = env['mail.message'].search([
            ('model', '=', 'crm.lead'),
            ('body', 'ilike', rel_p)
        ], limit=1)
        if existing_msg:
            continue

        # Find matching lead
        lead = env['crm.lead'].find_lead_by_phone(phone_10, active_test=False)
        if not lead:
            lead = env['crm.lead'].search([
                ('type', '=', 'opportunity'),
                ('phone', 'ilike', phone_10)
            ], limit=1)

        # If lead exists and recording not logged:
        if lead:
            file_date = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            player_url = f"https://crm.sigprop.in/play_recording?file={rel_p}"
            rec_url = f"https://crm.sigprop.in/recordings/{rel_p}"
            
            chatter_body = Markup(f"""
                <div style="padding: 10px 14px; border-left: 4px solid #16a34a; background: #f8fafc; border-radius: 6px; margin: 4px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="font-weight: 700; color: #16a34a; font-size: 13.5px;">
                            📞 Call Recording (Server Synced)
                        </span>
                        <span style="font-weight: 700; color: #16a34a; background: #dcfce7; padding: 2px 10px; border-radius: 12px; font-size: 12px;">
                            Audio Attached
                        </span>
                    </div>
                    <div style="font-size: 12px; color: #475569; margin-top: 5px;">
                        <b>Staff:</b> {lead.user_id.name if lead.user_id else "Sales Team"} &nbsp;|&nbsp;
                        <b>Company:</b> {lead.company_id.name or "Signature Properties"} &nbsp;|&nbsp;
                        <b>Client:</b> {lead.phone or phone_10}
                    </div>
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #cbd5e1;">
                        <div style="margin-top: 4px;">
                            <a href="{player_url}" target="_blank" style="display: inline-block; padding: 7px 16px; background-color: #2563eb; color: #ffffff !important; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #1d4ed8; margin-right: 8px;">
                                <span style="color: #ffffff !important; font-weight: bold;">▶️ Play Recording</span>
                            </a>
                            <a href="{rec_url}" download style="display: inline-block; padding: 7px 12px; background-color: #ffffff; color: #334155 !important; border: 1px solid #cbd5e1; border-radius: 6px; text-decoration: none; font-size: 11.5px; font-weight: bold;">
                                <span style="color: #334155 !important; font-weight: bold;">⬇️ Download</span>
                            </a>
                        </div>
                    </div>
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 3px;">
                        {file_date} &bull; Auto-Synced via Diya CRM Server Sync
                    </div>
                </div>
            """)

            lead.message_post(
                body=chatter_body,
                message_type="comment",
                subtype_xmlid="mail.mt_note",
                author_id=lead.user_id.partner_id.id if lead.user_id else admin_user.partner_id.id
            )
            newly_synced += 1

    env.cr.commit()
    print(f"🎉 Successfully created and attached {newly_synced} new call recording messages to CRM Leads!")
'''

    if os.name != 'nt' and hasattr(os, 'geteuid') and os.geteuid() == 0:
        shell_cmd = ["sudo", "-u", "odoo19", py_bin, odoo_bin, "shell", "-c", conf, "-d", "diyacrm", "--no-http"]
    else:
        shell_cmd = [py_bin, odoo_bin, "shell", "-c", conf, "-d", "diyacrm", "--no-http"]

    print("\n▶️ Running Odoo ORM shell sync...")
    try:
        res = subprocess.run(shell_cmd, input=shell_code, text=True, capture_output=True, timeout=180)
        if res.stdout:
            for line in res.stdout.splitlines():
                if any(k in line for k in ["Scanning", "Total Audio", "Updated", "Successfully", "Notice", "ERROR"]):
                    print(line)
        if res.stderr:
            err_lines = [l for l in res.stderr.splitlines() if "ERROR" in l or "Traceback" in l]
            if err_lines:
                print("⚠️ Errors encountered:")
                for l in err_lines[:5]:
                    print("  ", l)
    except Exception as e:
        print(f"❌ Execution failed: {e}")

    print("\n✅ All Done!")

if __name__ == "__main__":
    run()

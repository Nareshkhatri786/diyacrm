# -*- coding: utf-8 -*-
"""
Diya CRM: Helper script to update Signature Properties Company Logo in Odoo 19.
Usage:
    python3 scripts/update_signature_properties_logo.py
"""
import os
import sys
import base64
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

    # Fallback paths
    candidate_py = [
        "/opt/odoo19-venv/bin/python3",
        "/opt/odoo19/venv/bin/python3",
        "/opt/odoo19/odoo-venv/bin/python3",
        "/opt/odoo-venv/bin/python3",
        "/usr/bin/python3",
    ]
    py_found = next((p for p in candidate_py if os.path.exists(p)), sys.executable)
    odoo_bin_found = "/opt/odoo19/odoo/odoo-bin" if os.path.exists("/opt/odoo19/odoo/odoo-bin") else "/opt/odoo19/odoo-bin"
    return py_found, odoo_bin_found, "/etc/odoo19.conf"

def run():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    addon_dir = os.path.dirname(script_dir)
    logo_path = os.path.join(addon_dir, 'static', 'src', 'img', 'signature_logo.png')

    if not os.path.exists(logo_path):
        print(f"❌ Error: Logo file not found at {logo_path}")
        sys.exit(1)

    py_bin, odoo_bin, conf = find_odoo_execution_command()
    print("===================================================================")
    print(" 🚀 DIYA CRM: Updating Company Logo to 'Signature Properties'")
    print("===================================================================")
    print(f"• Python Binary : {py_bin}")
    print(f"• Odoo Binary   : {odoo_bin}")
    print(f"• Config File   : {conf}")
    print(f"• Logo Image    : {logo_path}")

    # Read base64 logo
    with open(logo_path, 'rb') as f:
        raw_logo = f.read()
        logo_b64 = base64.b64encode(raw_logo).decode('utf-8')

    # 1. Primary Method: Update via Odoo ORM (odoo-bin shell)
    # This automatically updates partner image, company logo_web, thumbnails & filestore
    shell_code = f"""
import base64
logo_b64 = "{logo_b64}"
company = env['res.company'].search([('name', 'ilike', 'Signature')], limit=1)
if not company:
    company = env['res.company'].search([], limit=1)

if company:
    company.write({{'logo': logo_b64}})
    env.cr.commit()
    print(f"✅ SUCCESS: Updated company logo for '{{company.name}}' (ID: {{company.id}})")
else:
    print("⚠️ WARNING: No company found in res.company")
"""

    if os.name != 'nt' and hasattr(os, 'geteuid') and os.geteuid() == 0:
        shell_cmd = ["sudo", "-u", "odoo19", py_bin, odoo_bin, "shell", "-c", conf, "-d", "diyacrm", "--no-http"]
    else:
        shell_cmd = [py_bin, odoo_bin, "shell", "-c", conf, "-d", "diyacrm", "--no-http"]

    print("\n▶️ Updating company logo using Odoo ORM...")
    orm_success = False
    try:
        res = subprocess.run(shell_cmd, input=shell_code, text=True, capture_output=True, timeout=60)
        if res.stdout:
            for line in res.stdout.splitlines():
                if "SUCCESS" in line or "WARNING" in line:
                    print(line)
        if "SUCCESS" in (res.stdout or ""):
            orm_success = True
    except Exception as e:
        print(f"⚠️ Odoo shell run notice: {e}")

    # 2. Fallback / Direct SQL Method if ORM shell wasn't reached
    if not orm_success:
        print("\n▶️ Applying direct database update for res_company.logo_web...")
        sql = f"""
DO $$
DECLARE
    comp_id INT;
BEGIN
    SELECT id INTO comp_id
    FROM res_company
    WHERE name ILIKE '%Signature%'
    LIMIT 1;

    IF comp_id IS NULL THEN
        SELECT id INTO comp_id FROM res_company LIMIT 1;
    END IF;

    IF comp_id IS NOT NULL THEN
        UPDATE res_company
        SET logo_web = convert_to('{logo_b64}', 'UTF8'),
            write_date = NOW()
        WHERE id = comp_id;

        RAISE NOTICE '✅ Successfully updated logo_web on res_company (ID: %)!', comp_id;
    ELSE
        RAISE NOTICE '⚠️ Company not found in res_company.';
    END IF;
END $$;
"""
        cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm"]
        try:
            res = subprocess.run(cmd, input=sql, text=True, capture_output=True)
            if res.stdout:
                print(res.stdout)
            if res.stderr:
                print(res.stderr)
        except Exception as e:
            print(f"Error executing psql: {e}")

    print("\n🎉 ALL DONE! Signature Properties logo is now updated.")

if __name__ == '__main__':
    run()

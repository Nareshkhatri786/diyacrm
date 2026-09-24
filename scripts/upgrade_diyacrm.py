# -*- coding: utf-8 -*-
import os
import sys
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
                                odoo_bin = parts[1] if len(parts) > 1 and parts[1].endswith(".py") or "odoo-bin" in parts[1] else "/opt/odoo19/odoo/odoo-bin"
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

def main():
    print("===================================================================")
    print(" 🚀 DIYA CRM: Automatic Module Upgrade & Service Restart")
    print("===================================================================")

    py_bin, odoo_bin, conf = find_odoo_execution_command()
    print(f"• Python Binary : {py_bin}")
    print(f"• Odoo Binary   : {odoo_bin}")
    print(f"• Config File   : {conf}")

    extra_args = ["--logfile="]
    if os.name != 'nt' and hasattr(os, 'geteuid') and os.geteuid() == 0:
        upgrade_cmd = ["sudo", "-u", "odoo19", py_bin, odoo_bin, "-c", conf, "-d", "diyacrm", "-u", "diyacrm", "--stop-after-init"] + extra_args
    else:
        upgrade_cmd = [py_bin, odoo_bin, "-c", conf, "-d", "diyacrm", "-u", "diyacrm", "--stop-after-init"] + extra_args

    print("\n🛑 Temporarily Stopping Odoo19 Service to release port...")
    subprocess.run(["systemctl", "stop", "odoo19"])

    print(f"\n📦 Running Command: {' '.join(upgrade_cmd)}")
    res = subprocess.run(upgrade_cmd)
    if res.returncode == 0:
        print("✅ Module Upgrade Succeeded!")
    else:
        print(f"⚠️ Upgrade finished with code {res.returncode}")
        # Print recent log lines from log file
        for log_candidate in ["/var/log/odoo/odoo19.log", "/var/log/odoo/odoo.log"]:
            if os.path.exists(log_candidate):
                print(f"\n--- Recent entries from {log_candidate} ---")
                subprocess.run(["tail", "-n", "35", log_candidate])

    print("\n▶️ Starting Odoo19 Service...")
    subprocess.run(["systemctl", "start", "odoo19"])
    print("\n🎉 ALL DONE! Diya CRM Unit Matrix is now LIVE!")

if __name__ == '__main__':
    main()

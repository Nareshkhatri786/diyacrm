# -*- coding: utf-8 -*-
import os
import glob
import subprocess
import gzip

def check_traffic_and_config():
    print("==========================================================================")
    print(" 🔍 CHECKING NGINX & ODOO CONFIG & WEBHOOK TRAFFIC")
    print("==========================================================================")

    # 1. Check /etc/odoo19.conf
    if os.path.exists('/etc/odoo19.conf'):
        print("\n📄 1. /etc/odoo19.conf relevant settings:")
        try:
            with open('/etc/odoo19.conf', 'r') as f:
                for line in f:
                    if any(k in line.lower() for k in ['logfile', 'log_level', 'log_handler', 'db_name', 'addons_path']):
                        print(f"   {line.strip()}")
        except Exception as e:
            print(f"   Error reading conf: {e}")

    # 2. Check Nginx log files
    print("\n🌐 2. Checking Nginx log files in /var/log/nginx/:")
    nginx_files = glob.glob('/var/log/nginx/*')
    for nf in nginx_files:
        try:
            sz = os.path.getsize(nf)
            print(f"   • {nf} ({sz} bytes)")
        except Exception:
            pass

    # Search Nginx logs for any POST requests in last 10 days
    print("\n🌐 3. Searching ALL Nginx logs for webhook/meta/whatsapp hits:")
    total_hits = 0
    for nf in nginx_files:
        if 'error' in nf:
            continue
        try:
            if nf.endswith('.gz'):
                f = gzip.open(nf, 'rt', errors='ignore')
            else:
                f = open(nf, 'r', errors='ignore')

            matching = []
            for line in f:
                if any(k in line for k in ['webhook', 'whatsapp', 'inbound', 'lead']):
                    matching.append(line.strip())
            f.close()

            if matching:
                print(f"\n   Found {len(matching)} hit(s) in {nf}:")
                for m in matching[-10:]:
                    print(f"     {m}")
                total_hits += len(matching)
        except Exception as e:
            pass

    if total_hits == 0:
        print("   ⚠️ No hits matching 'webhook', 'whatsapp', 'inbound', or 'lead' found in Nginx access logs!")
        print("   Checking recent general POST requests to see where traffic is going:")
        for nf in nginx_files:
            if 'access' in nf and not nf.endswith('.gz'):
                try:
                    cmd = f"grep 'POST ' {nf} | tail -n 15"
                    out = subprocess.check_output(cmd, shell=True, text=True)
                    if out.strip():
                        print(f"   Recent POST requests in {nf}:")
                        for l in out.strip().split('\n')[:10]:
                            print(f"     {l}")
                except Exception:
                    pass

    # 3. Check /tmp/odoo_logs.txt created earlier
    if os.path.exists('/tmp/odoo_logs.txt'):
        sz = os.path.getsize('/tmp/odoo_logs.txt')
        print(f"\n📁 4. /tmp/odoo_logs.txt size: {sz} bytes")
        try:
            cmd = "grep -i -E 'webhook|whatsapp' /tmp/odoo_logs.txt | tail -n 20"
            out = subprocess.check_output(cmd, shell=True, text=True)
            if out.strip():
                print(f"   Lines mentioning webhook/whatsapp in /tmp/odoo_logs.txt:")
                for l in out.strip().split('\n'):
                    print(f"     {l}")
            else:
                print("   No lines mentioning webhook/whatsapp in /tmp/odoo_logs.txt")
        except Exception as e:
            print(f"   Error grepping /tmp/odoo_logs.txt: {e}")

    # 4. Check crontab or php forwarder scripts
    print("\n⚙️ 5. Checking for any PHP or custom webhook forwarder scripts:")
    for path in ['/var/www/html', '/var/www', '/opt']:
        php_files = glob.glob(f"{path}/**/*.php", recursive=True)
        inbound_phps = [p for p in php_files if 'inbound' in p or 'whatsapp' in p]
        if inbound_phps:
            print(f"   Found in {path}: {inbound_phps}")

    print("\n==========================================================================")
    print(" ✅ TRAFFIC CHECK COMPLETED")
    print("==========================================================================")

if __name__ == '__main__':
    check_traffic_and_config()

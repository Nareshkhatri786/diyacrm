# -*- coding: utf-8 -*-
"""
Diya CRM: Test WhatsApp Sending directly on Lead 9316217750
Uses Odoo ORM or direct DB to test and report exact result.
"""
import subprocess
import sys

def run():
    print("==================================================================")
    print(" 📲 TESTING WHATSAPP SENDING ON LEAD 9316217750")
    print("==================================================================")

    # 1. First, restart odoo19 so in-memory ORM cache is completely cleared
    print("1. Restarting Odoo service to reload new tokens from DB into RAM...")
    subprocess.run(["sudo", "systemctl", "restart", "odoo19"], check=False)
    print("   ✅ Odoo service restarted!")

    # 2. Check lead in DB
    sql_check = """
    SELECT l.id, l.name, l.phone, c.name AS company, c.id AS comp_id
    FROM crm_lead l
    JOIN res_company c ON c.id = l.company_id
    WHERE l.phone LIKE '%9316217750%'
    LIMIT 3;
    """
    res = subprocess.run(["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql_check], capture_output=True, text=True)
    print("\n2. Lead Details in Database:")
    print(res.stdout)

    # 3. Test Meta WhatsApp API directly from Python on server to 919316217750
    import urllib.request
    import json

    token_sql = "SELECT value FROM ir_config_parameter WHERE key = 'diyacrm.shreemad_family.token';"
    token_res = subprocess.run(["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-t", "-A", "-c", token_sql], capture_output=True, text=True)
    token = token_res.stdout.strip()
    phone_id = "1161115510429761"
    recipient = "919316217750"

    print(f"\n3. Testing Meta Graph API directly with Shreemad Token (Length: {len(token)})...")
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": {
            "name": "payment_received",
            "language": {"code": "en"},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "*Valued Client*, thank you for talking with us regarding *Shreemad Family*"},
                    {"type": "text", "text": "are sharing the project details with you. For any help, please contact our team"},
                    {"type": "text", "text": "more details, check brochure and video here: https://drive.google.com/file/d/1vN7R6AqyZRAiTOVdg4gK9C_mRo9jkHWM/view"}
                ]
            }]
        }
    }

    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"   🎉 SUCCESS: WhatsApp Delivered to {recipient}!")
            print(f"   Meta Response: {data}")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"   ❌ Meta Error ({e.code}): {err}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == '__main__':
    run()

# -*- coding: utf-8 -*-
"""
Diya CRM: Direct Meta WhatsApp Token Validator
Reads tokens directly via psql query and checks them with Meta Graph API.
"""
import sys
import os
import subprocess
import json
import urllib.request
import urllib.error

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECTS = [
    {
        "name": "The 1st Residency (Radhe Developers)",
        "phone_key": "diyacrm.radhe_developers.phone_id",
        "token_key": "diyacrm.radhe_developers.token",
        "default_phone": "1305619522636450"
    },
    {
        "name": "Devi Bungalows",
        "phone_key": "diyacrm.devi_bungalows.phone_id",
        "token_key": "diyacrm.devi_bungalows.token",
        "default_phone": "1265084363352795"
    },
    {
        "name": "Shreemad Family",
        "phone_key": "diyacrm.shreemad_family.phone_id",
        "token_key": "diyacrm.shreemad_family.token",
        "default_phone": "1161115510429761"
    },
    {
        "name": "Royal Rudraksha",
        "phone_key": "diyacrm.royal_rudraksha.phone_id",
        "token_key": "diyacrm.royal_rudraksha.token",
        "default_phone": "1224814500716320"
    },
    {
        "name": "Signature Properties",
        "phone_key": "diyacrm.signature_properties.phone_id",
        "token_key": "diyacrm.signature_properties.token",
        "default_phone": "1193758907159434"
    }
]

def get_db_param(key):
    sql = f"SELECT value FROM ir_config_parameter WHERE key = '{key}';"
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-t", "-A", "-c", sql]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return ""

def test_meta_token(name, phone_id, token):
    print("------------------------------------------------------------------")
    print(f"🏢 Project: {name}")
    print(f"   Phone Number ID: {phone_id}")
    if not token:
        print("   ❌ Token is MISSING in ir_config_parameter!")
        return

    print(f"   Token: {token[:12]}...{token[-6:]} (Length: {len(token)})")

    # Test 1: Check Token Identity via /me or phone number endpoint
    url = f"https://graph.facebook.com/v19.0/{phone_id}?fields=id,verified_name,display_phone_number,quality_rating,code_verification_status"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("   ✅ META TOKEN STATUS: ACTIVE & VALID!")
            print(f"      • Verified Business Name: {data.get('verified_name', 'N/A')}")
            print(f"      • Display Phone:          {data.get('display_phone_number', 'N/A')}")
            print(f"      • Quality Rating:          {data.get('quality_rating', 'N/A')}")
            print(f"      • Verification Status:     {data.get('code_verification_status', 'N/A')}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        try:
            err_json = json.loads(err_body)
            err_obj = err_json.get('error', {})
            err_msg = err_obj.get('message', err_body)
            err_code = err_obj.get('code', '')
            err_subcode = err_obj.get('error_subcode', '')
            print(f"   ❌ META TOKEN STATUS: FAILED (HTTP {e.code})")
            print(f"      • Error Code:    {err_code} (Subcode: {err_subcode})")
            print(f"      • Error Message: {err_msg}")
            if err_code == 190:
                print("      👉 ROOT CAUSE: Access Token has EXPIRED or been REVOKED by Meta!")
                print("         Need to generate a fresh Permanent System User Token from Meta Business Manager.")
        except Exception:
            print(f"   ❌ HTTP {e.code}: {err_body}")
    except Exception as e:
        print(f"   ❌ Network/Connection error: {e}")

def main():
    print("==================================================================")
    print(" 🔍 DIYA CRM: LIVE META WHATSAPP TOKEN VERIFICATION")
    print("==================================================================")

    for p in PROJECTS:
        phone_id = get_db_param(p["phone_key"]) or p["default_phone"]
        token = get_db_param(p["token_key"])
        test_meta_token(p["name"], phone_id, token)

    print("\n==================================================================")

if __name__ == '__main__':
    main()

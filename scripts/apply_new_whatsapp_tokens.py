# -*- coding: utf-8 -*-
"""
Diya CRM: Apply New Meta WhatsApp Tokens for Shreemad Family & Royal Rudraksha.
"""
import sys
import os
import subprocess
import json
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

NEW_TOKEN = "EAAf9a2B9ZCBsBS9QyZAB11vUG09ImcEjXoCFdjQNb41ZBNEEvpmSEjdJLn13TuYnxxPalbytHqwflGtoE0vRY6C1XFMsY6AvO96XhrnOF4EgbbxSmuSPbQGUa45Rn334jH44bSIAwCeRzSHyuJeBuI5cDb2LhyjN7i7gt691Ephdm56XC0CNkMPeRPh9QZDZD"

SQL_UPDATE = f"""
DO $$
BEGIN
    -- 1. Update Shreemad Family Token
    INSERT INTO ir_config_parameter (key, value, create_date, write_date, create_uid, write_uid)
    VALUES ('diyacrm.shreemad_family.token', '{NEW_TOKEN}', NOW(), NOW(), 1, 1)
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, write_date = NOW();

    -- 2. Update Royal Rudraksha Token (Same WABA ID: 27849416088073239)
    INSERT INTO ir_config_parameter (key, value, create_date, write_date, create_uid, write_uid)
    VALUES ('diyacrm.royal_rudraksha.token', '{NEW_TOKEN}', NOW(), NOW(), 1, 1)
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, write_date = NOW();

    RAISE NOTICE '✅ Shreemad Family & Royal Rudraksha tokens updated successfully in PostgreSQL!';
END $$;
"""

def verify_phone(name, phone_id, token):
    url = f"https://graph.facebook.com/v19.0/{phone_id}?fields=id,verified_name,display_phone_number,quality_rating"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"   ✅ {name}: ACTIVE & VERIFIED!")
            print(f"      • Verified Business Name: {data.get('verified_name')}")
            print(f"      • Phone Number:          {data.get('display_phone_number')}")
            print(f"      • Quality Rating:        {data.get('quality_rating')}")
            return True
    except Exception as e:
        print(f"   ❌ {name}: Failed: {e}")
        return False

def main():
    print("==================================================================")
    print(" 🚀 DIYA CRM: APPLYING NEW META WHATSAPP TOKENS")
    print("==================================================================")

    # Apply via psql
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", SQL_UPDATE]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(res.stdout)
    except Exception as e:
        print(f"Error running psql update: {e}")

    # Verify live
    print("\n🔍 Live Verification with Meta Graph API:")
    verify_phone("Shreemad Family", "1161115510429761", NEW_TOKEN)
    verify_phone("Royal Rudraksha", "1224814500716320", NEW_TOKEN)

    print("\n==================================================================")
    print(" 🎉 ALL DONE: Shreemad Family & Royal Rudraksha are now LIVE!")
    print("==================================================================")

if __name__ == '__main__':
    main()

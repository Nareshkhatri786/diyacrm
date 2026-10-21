# -*- coding: utf-8 -*-
"""
Diya CRM: WhatsApp Multi-Project Diagnostic Tool
Checks config params in DB, inspects recent failure logs, and tests Meta API token validity for each project.
"""
import sys
import os
import subprocess
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SQL_DIAGNOSTIC = """
DO $$
DECLARE
    r RECORD;
    v_cnt INT;
BEGIN
    RAISE NOTICE '==================================================================';
    RAISE NOTICE ' 🔍 DIYA CRM: WHATSAPP CONFIGURATION & FAILURE AUDIT';
    RAISE NOTICE '==================================================================';

    -- 1. Check Config Parameters
    RAISE NOTICE '';
    RAISE NOTICE '1. STORED WHATSAPP PARAMETERS IN IR_CONFIG_PARAMETER:';
    FOR r IN (
        SELECT key, value
        FROM ir_config_parameter
        WHERE key LIKE 'diyacrm.%.token' OR key LIKE 'diyacrm.%.phone_id'
        ORDER BY key
    ) LOOP
        IF r.key LIKE '%.token' THEN
            RAISE NOTICE '   • % = % (Length: % chars)', 
                r.key, 
                CONCAT(SUBSTRING(r.value FROM 1 FOR 10), '...', SUBSTRING(r.value FROM LENGTH(r.value)-6 FOR 7)),
                LENGTH(r.value);
        ELSE
            RAISE NOTICE '   • % = %', r.key, r.value;
        END IF;
    END LOOP;

    -- 2. Recent WhatsApp Failures from Chatter (Last 20)
    RAISE NOTICE '';
    RAISE NOTICE '2. RECENT WHATSAPP FAILURE NOTICES IN CHATTER (LAST 10):';
    FOR r IN (
        SELECT id, res_id, date, SUBSTRING(body FROM 1 FOR 300) AS body_sub
        FROM mail_message
        WHERE model = 'crm.lead'
          AND (body ILIKE '%WhatsApp Failed%' OR body ILIKE '%Meta API error%')
        ORDER BY id DESC
        LIMIT 10
    ) LOOP
        RAISE NOTICE '   --------------------------------------------------------------';
        RAISE NOTICE '   [Msg #%] Date: % | Lead #%', r.id, r.date, r.res_id;
        RAISE NOTICE '   % ', r.body_sub;
    END LOOP;

    -- 3. Last Outbound WhatsApp Activity per Project
    RAISE NOTICE '';
    RAISE NOTICE '3. LAST OUTBOUND WHATSAPP SENT PER COMPANY:';
    FOR r IN (
        SELECT 
            c.name AS company_name,
            count(m.id) AS total_outbound,
            max(m.date) AS last_sent_at
        FROM res_company c
        LEFT JOIN crm_lead l ON l.company_id = c.id
        LEFT JOIN crm_lead_whatsapp_message m ON m.lead_id = l.id AND m.direction = 'outbound'
        GROUP BY c.name
        ORDER BY c.name
    ) LOOP
        RAISE NOTICE '   • %: Total Outbound = % | Last Sent: %', 
            r.company_name, r.total_outbound, COALESCE(r.last_sent_at::text, 'Never');
    END LOOP;

    RAISE NOTICE '==================================================================';
END $$;

-- Query to dump config as JSON for Python Meta API verification
SELECT json_agg(t) AS config_json
FROM (
    SELECT key, value 
    FROM ir_config_parameter 
    WHERE key LIKE 'diyacrm.%.token' OR key LIKE 'diyacrm.%.phone_id'
) t;
"""

def test_meta_api(phone_id, token, project_name):
    import urllib.request
    import urllib.error
    
    print(f"\n🌐 Testing Meta API for '{project_name}'...")
    print(f"   Phone ID: {phone_id}")
    if not token:
        print("   ❌ ERROR: Token is EMPTY or NOT CONFIGURED in ir_config_parameter!")
        return
    print(f"   Token: {token[:10]}...{token[-6:]} (Length: {len(token)})")

    url = f"https://graph.facebook.com/v19.0/{phone_id}?fields=id,verified_name,display_phone_number,quality_rating,code_verification_status"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            print("   ✅ Meta API Connection: SUCCESSFUL!")
            print(f"      • Verified Name: {data.get('verified_name', 'N/A')}")
            print(f"      • Display Phone: {data.get('display_phone_number', 'N/A')}")
            print(f"      • Quality Rating: {data.get('quality_rating', 'N/A')}")
            print(f"      • Code Status: {data.get('code_verification_status', 'N/A')}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        print(f"   ❌ Meta API HTTP Error {e.code}:")
        try:
            err_json = json.loads(err_body)
            err_msg = err_json.get('error', {}).get('message', err_body)
            err_type = err_json.get('error', {}).get('type', '')
            err_code = err_json.get('error', {}).get('code', '')
            err_subcode = err_json.get('error', {}).get('error_subcode', '')
            print(f"      • Message:  {err_msg}")
            print(f"      • Type:     {err_type}")
            print(f"      • Code:     {err_code} (Subcode: {err_subcode})")
        except Exception:
            print(f"      • Details: {err_body}")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")

def run():
    if os.name != 'nt':
        cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", SQL_DIAGNOSTIC]
    else:
        cmd = ["psql", "-U", "postgres", "-d", "odoo19", "-c", SQL_DIAGNOSTIC]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(res.stdout)
        if res.stderr:
            print(res.stderr)
            
        # Parse JSON output to run Meta API tests
        lines = res.stdout.splitlines()
        for idx, line in enumerate(lines):
            line_str = line.strip()
            if line_str.startswith('[{"key":') or line_str.startswith('[{'):
                try:
                    configs = json.loads(line_str)
                    cfg_map = {item['key']: item['value'] for item in configs}
                    
                    projects = [
                        ("Shreemad Family", 'diyacrm.shreemad_family.phone_id', 'diyacrm.shreemad_family.token', '1161115510429761'),
                        ("Royal Rudraksha", 'diyacrm.royal_rudraksha.phone_id', 'diyacrm.royal_rudraksha.token', '1224814500716320'),
                        ("The 1st Residency (Radhe Developers)", 'diyacrm.radhe_developers.phone_id', 'diyacrm.radhe_developers.token', '1305619522636450'),
                        ("Devi Bungalows", 'diyacrm.devi_bungalows.phone_id', 'diyacrm.devi_bungalows.token', '1265084363352795'),
                    ]
                    
                    print("\n==================================================================")
                    print(" 📡 LIVE META GRAPH API VERIFICATION (ALL PROJECTS)")
                    print("==================================================================")
                    for name, pid_key, tok_key, default_pid in projects:
                        pid = cfg_map.get(pid_key, default_pid)
                        tok = cfg_map.get(tok_key, '')
                        test_meta_api(pid, tok, name)
                except Exception as e:
                    print(f"Error parsing json config: {e}")
                break
    except Exception as e:
        print(f"Error running psql diagnostic: {e}")

if __name__ == '__main__':
    run()

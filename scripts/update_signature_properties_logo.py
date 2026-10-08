# -*- coding: utf-8 -*-
"""
Diya CRM: Helper script to update Signature Properties Company Logo in PostgreSQL.
Usage:
    python3 scripts/update_signature_properties_logo.py
"""
import os
import sys
import base64
import subprocess

def run():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    addon_dir = os.path.dirname(script_dir)
    logo_path = os.path.join(addon_dir, 'static', 'src', 'img', 'signature_logo.png')

    if not os.path.exists(logo_path):
        print(f"❌ Error: Logo file not found at {logo_path}")
        sys.exit(1)

    with open(logo_path, 'rb') as f:
        logo_b64 = base64.b64encode(f.read()).decode('utf-8')

    sql = f"""
DO $$
DECLARE
    comp_id INT;
    p_id INT;
BEGIN
    -- 1. Find Signature Properties Company
    SELECT id, partner_id INTO comp_id, p_id
    FROM res_company
    WHERE name ILIKE '%Signature%'
    LIMIT 1;

    IF comp_id IS NOT NULL THEN
        -- Update company logo
        UPDATE res_company
        SET logo = decode('{logo_b64}', 'base64')
        WHERE id = comp_id;

        -- Update company partner avatar/logo
        IF p_id IS NOT NULL THEN
            UPDATE res_partner
            SET image_1920 = decode('{logo_b64}', 'base64')
            WHERE id = p_id;
        END IF;

        RAISE NOTICE '✅ Successfully updated Logo for Company "Signature Properties" (ID: %)!', comp_id;
    ELSE
        RAISE NOTICE '⚠️ Company "Signature Properties" not found in res_company.';
    END IF;
END $$;

SELECT id, name, partner_id, (logo IS NOT NULL) AS has_logo
FROM res_company
WHERE name ILIKE '%Signature%';
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

if __name__ == '__main__':
    run()

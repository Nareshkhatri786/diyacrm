# -*- coding: utf-8 -*-
import sys
import subprocess

phone = sys.argv[1] if len(sys.argv) > 1 else '9227777314'
digits = "".join(filter(str.isdigit, phone))
phone_10 = digits[-10:] if len(digits) >= 10 else digits

if not phone_10:
    print("❌ Invalid phone number.")
    sys.exit(1)

sql_command = f"""
DO $$
DECLARE
    rec RECORD;
    primary_id INT;
    dup_id INT;
    dup_count INT := 0;
BEGIN
    FOR rec IN
        SELECT company_id, 
               array_agg(id ORDER BY active DESC, id ASC) as lead_ids
        FROM crm_lead
        WHERE RIGHT(regexp_replace(COALESCE(phone, ''), '\\D', '', 'g'), 10) = '{phone_10}'
        GROUP BY company_id
        HAVING count(id) > 1
    LOOP
        primary_id := rec.lead_ids[1];
        RAISE NOTICE 'Merging for Company %: Primary Lead ID is %', rec.company_id, primary_id;
        
        FOR i IN 2..array_length(rec.lead_ids, 1) LOOP
            dup_id := rec.lead_ids[i];
            RAISE NOTICE 'Moving chatter and activities from Duplicate #% to Primary #%', dup_id, primary_id;
            
            UPDATE mail_message SET res_id = primary_id WHERE model = 'crm.lead' AND res_id = dup_id;
            UPDATE mail_activity SET res_id = primary_id WHERE res_model = 'crm.lead' AND res_id = dup_id;
            DELETE FROM crm_lead WHERE id = dup_id;
            dup_count := dup_count + 1;
        END LOOP;
        
        UPDATE crm_lead SET phone = '{phone_10}' WHERE id = primary_id;
    END LOOP;
    
    IF dup_count > 0 THEN
        RAISE NOTICE '🎉 Successfully merged and removed % duplicate lead(s) for %!', dup_count, '{phone_10}';
    ELSE
        RAISE NOTICE 'ℹ️ No duplicates found for phone % in the same company.', '{phone_10}';
    END IF;
END $$;
"""

print(f"Executing duplicate merge for phone {phone_10} in database 'diyacrm'...")
try:
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql_command]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)
except Exception as e:
    print("Error executing psql:", str(e))

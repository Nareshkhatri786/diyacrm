# -*- coding: utf-8 -*-
import sys
import subprocess

merge_mode = '--merge' in sys.argv

sql_scan = """
SELECT 
    c.name AS company_name,
    RIGHT(regexp_replace(COALESCE(l.phone, ''), '\\D', '', 'g'), 10) AS phone_10,
    COUNT(l.id) AS dup_count,
    string_agg(l.id::text, ', ' ORDER BY l.id ASC) AS lead_ids,
    string_agg(l.name || ' [' || COALESCE(s.name, 'No Stage') || ']', '  |  ' ORDER BY l.id ASC) AS details
FROM crm_lead l
JOIN res_company c ON c.id = l.company_id
LEFT JOIN crm_stage s ON s.id = l.stage_id
WHERE l.phone IS NOT NULL 
  AND length(regexp_replace(l.phone, '\\D', '', 'g')) >= 10
GROUP BY c.name, l.company_id, RIGHT(regexp_replace(COALESCE(l.phone, ''), '\\D', '', 'g'), 10)
HAVING COUNT(l.id) > 1
ORDER BY c.name, COUNT(l.id) DESC;
"""

sql_merge_all = """
DO $$
DECLARE
    rec RECORD;
    primary_id INT;
    dup_id INT;
    total_merged INT := 0;
    group_count INT := 0;
BEGIN
    FOR rec IN
        SELECT company_id, 
               RIGHT(regexp_replace(COALESCE(phone, ''), '\\D', '', 'g'), 10) as clean_phone,
               array_agg(id ORDER BY active DESC, id ASC) as lead_ids
        FROM crm_lead
        WHERE phone IS NOT NULL AND length(regexp_replace(phone, '\\D', '', 'g')) >= 10
        GROUP BY company_id, RIGHT(regexp_replace(COALESCE(phone, ''), '\\D', '', 'g'), 10)
        HAVING count(id) > 1
    LOOP
        primary_id := rec.lead_ids[1];
        group_count := group_count + 1;
        
        FOR i IN 2..array_length(rec.lead_ids, 1) LOOP
            dup_id := rec.lead_ids[i];
            
            -- Move chatter and activities
            UPDATE mail_message SET res_id = primary_id WHERE model = 'crm.lead' AND res_id = dup_id;
            UPDATE mail_activity SET res_id = primary_id WHERE res_model = 'crm.lead' AND res_id = dup_id;
            
            -- Remove duplicate
            DELETE FROM crm_lead WHERE id = dup_id;
            total_merged := total_merged + 1;
        END LOOP;
        
        -- Normalize primary lead phone
        UPDATE crm_lead SET phone = rec.clean_phone WHERE id = primary_id;
    END LOOP;
    
    RAISE NOTICE '🎉 Successfully cleaned % duplicate groups, merged and deleted % duplicate leads!', group_count, total_merged;
END $$;
"""

if merge_mode:
    print("🚀 Merging ALL duplicates across all companies...")
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql_merge_all]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)
else:
    print("🔍 Scanning for duplicate phone numbers in the SAME company...")
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql_scan]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)
    print("\n💡 NOTE: To automatically merge all found duplicates and preserve all chatter notes:")
    print("   python3 scripts/scan_all_duplicates.py --merge")

# -*- coding: utf-8 -*-
"""
Diya CRM: Migrate previous WhatsApp messages from Chatter (mail_message) to crm_lead_whatsapp_message table and clean up Chatter.
"""
import subprocess

def run_migration():
    print("===================================================================")
    print(" 🚀 Migrating Existing WhatsApp Messages from Chatter to Tab")
    print("===================================================================")
    sql = """
DO $$
DECLARE
    rec RECORD;
    migrated_count INT := 0;
    cleaned_body TEXT;
    author_name_val TEXT;
    phone_val TEXT;
BEGIN
    FOR rec IN 
        SELECT m.id, m.res_id as lead_id, m.date, m.body, p.name as author_name, l.phone as lead_phone
        FROM mail_message m
        JOIN crm_lead l ON l.id = m.res_id
        LEFT JOIN res_partner p ON p.id = m.author_id
        WHERE m.model = 'crm.lead' 
          AND (m.body ILIKE '%New WhatsApp Message%' OR m.body ILIKE '%Inbound WhatsApp Message%')
        ORDER BY m.id ASC
    LOOP
        -- Extract clean message text from html
        cleaned_body := regexp_replace(rec.body, '<[^>]+>', ' ', 'g');
        cleaned_body := replace(cleaned_body, '📱 New WhatsApp Message:', '');
        cleaned_body := replace(cleaned_body, '📱 Inbound WhatsApp Message:', '');
        cleaned_body := trim(cleaned_body);

        author_name_val := COALESCE(rec.author_name, 'Client');
        phone_val := COALESCE(rec.lead_phone, '');

        IF cleaned_body IS NOT NULL AND cleaned_body != '' THEN
            INSERT INTO crm_lead_whatsapp_message (lead_id, direction, author_name, phone, body, date)
            VALUES (rec.lead_id, 'inbound', author_name_val, phone_val, cleaned_body, rec.date);

            -- Clean up from mail_message so chatter is clean
            DELETE FROM mail_message WHERE id = rec.id;

            migrated_count := migrated_count + 1;
        END IF;
    END LOOP;

    RAISE NOTICE '✅ Successfully migrated and cleaned % WhatsApp message(s) from Chatter to the WhatsApp History tab!', migrated_count;
END $$;
"""
    cmd = ["sudo", "-u", "postgres", "psql", "-d", "diyacrm", "-c", sql]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print(res.stderr)

if __name__ == '__main__':
    run_migration()
